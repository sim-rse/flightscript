import numpy as np
import itertools
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from pointlib import loadWaypoints, WayPoint, Link, NoFlyZone
from rich import print
from energyCalc import *

# =========================
# USER PARAMETERS
# ========================='

EMPTY_MASS = 1.5691  # kg
BATTERY_ENERGY = 74 * 3600  #multiply Wh by 3600 to get the energy in Joules
MAX_PAYLOAD = 0.6

# --- Flight profile ---
CRUISE_ALTITUDE = 30.0
SAFETY_RESERVE = 0.15

# --- needed for acceleration calculations etc in mathematics.py---
CD = 1
RHO = 1.225
KANTELHOEK = 20
A = 0.05

MAXLIFT = 7.87696893

# --- Loading Waypoints and selecting BASE ---
waypoints, noflyzones, BASE = loadWaypoints("waypoints.json")

# =========================
# ENERGY MODEL
# =========================

def power_required(lift):
    return 1.231073846*(lift**2) + 7.431724825*lift - 2.405185698       #quadratic regression of power in function of the lift (from experimental results)
    #return A * (mass ** 1.5) + B

def climb_energy(mass):
    power_to_counter_grav = power_required(lift_vert(mass))
    
    a_v, v_v = a_vert(mass), v_vert(mass)
    d_v = a_v

    T_up = travel_time(CRUISE_ALTITUDE, v_v, a_v)

    lift = (a_v+d_v)*mass
    #t = CRUISE_ALTITUDE / CLIMB_RATE
    return power_required(lift) * T_up

def descent_energy(mass):
    power_to_counter_grav = power_required(lift_vert(mass))

    a_v, v_v = a_vert(mass), v_vert(mass)
    d_v = a_v
    T_down = travel_time(CRUISE_ALTITUDE, v_v, a_v)

    lift = (a_v+d_v)*mass
    #t = CRUISE_ALTITUDE / DESCENT_RATE
    return power_required(lift) * T_down

def energy_for_leg(distance, mass):
    v_h = v_hor(mass)
    a_h = a_hor(mass)
    d_h = a_h

    power_to_counter_grav = power_required(lift_vert(mass))
    lift = 2*a_h*mass
    power_to_move = power_required(lift)
    total_power = power_to_counter_grav + power_to_move
    #time = distance / CRUISE_SPEED
    T_horizontal = travel_time(distance, v_h, a_h)
    return total_power* T_horizontal

# =========================
# LINK MATRIX
# =========================
def get_links_and_dist(points):
    n = len(points)
    links = np.full((n, n), None, dtype=object) #create empty matrix with only "None"'s

    distances = np.zeros((n, n))

    for i in range(n):
        #only iterating for the upper triangle of the matrix (and doing the lower at the same time)
        for j in range(i+1,n):      #i+1 for skipping the diagonal
            value = Link(points[i],points[j])
            dist = value.length()

            links[i][j] = value
            links[j][i] = value

            distances[i,j] = dist
            distances[j,i] = dist

    return links, distances
            
links, distance_matrix = get_links_and_dist(waypoints)
#print(f"Distance matrix: {distance_matrix}")
# =========================
# ROUTE ENERGY
# =========================

def route_energy(route):
    #print(f"[route_energy] Route: {route} waypoints: {waypoints}")
    payload_subset = [point.payload for point in route]     #the total payload list needed for this route
    remaining_payload = sum(payload_subset)
    total_mass = EMPTY_MASS + remaining_payload

    energy = 0.0

    # takeoff climb
    energy += climb_energy(total_mass)

    for i in range(len(route) - 1):
        a:WayPoint = route[i] 
        b:WayPoint = route[i+1]
        #print(f"a :{a}, b: {b}\nindex a :{a.idx} index b: {b.idx}\ntype: {type(a.idx)}")
        d = distance_matrix[a.idx, b.idx]

        #travelling to waypoint
        energy += energy_for_leg(d, total_mass)

        # payload drop
        energy += descent_energy(total_mass)


        remaining_payload -= b.payload              #the last waypoint is back to the origin, but the payload there is 0 so no problem
        total_mass = EMPTY_MASS + remaining_payload
        
        if i+1 != len(route):       #won't take off at the last step
            #take off again
            energy += climb_energy(total_mass)

    return energy

# =========================
# best path
# =========================

def iterative_deepening(waypoints, startpoint):         #iterative deepening
    remaining = [i for i in waypoints if i != startpoint]
    route = [startpoint]
    while remaining != []:
        
        energy = float("inf")

        for point in remaining:     #depth = 1
            new_route = route + [point]
            
            if len(remaining)<=1:
                new_energy = route_energy(new_route)
                if  new_energy < energy:
                    energy = new_energy
                    best_new_route = new_route
            else:
                remaining2 = [i for i in waypoints if i not in new_route]
                for point2 in remaining2:       #depth = 2
                    new_route2  = new_route + [point2]
                    new_energy = route_energy(new_route2)
                    if  new_energy < energy:
                        energy = new_energy
                        best_new_route = new_route      #only keeps the next row of the best option, we'll reiterate later with that new point and the two next rows  
        
        route = best_new_route
        remaining = [i for i in waypoints if i not in route]

        """print(f"found new best route: {route}")
        print(f"remaining: {remaining}")
        input()"""

    route.append(BASE)
    return route

def breadth_first(waypoints:list, startpoint):
    remaining = [point for point in waypoints if not point == startpoint]
    energy = float('inf')
    route = None
    print(f"getting all permutations of {remaining}")
    for combination in itertools.permutations(remaining):
        new_route = [startpoint]+list(combination)+[startpoint]
        new_energy = route_energy(new_route)
        if new_energy < energy:
            route = new_route
            energy = new_energy
            #print(f"[[red bold]![/red bold]] found new best route: {route}")
    return route

# =========================
# OR-TOOLS ROUTE
# =========================

def solve_route(sub_points:tuple, startpoint):
    
    #print("Sub points ", sub_points)

    n = len(sub_points)
    indx = sub_points.index(startpoint)
    manager = pywrapcp.RoutingIndexManager(n, 1, indx)     #n nodes and we have one drone starting at node 0 (this means the first element in the list we give)
    routing = pywrapcp.RoutingModel(manager)            #some kind of initialization 

    def distance_callback(from_index, to_index):
        f = manager.IndexToNode(from_index)
        t = manager.IndexToNode(to_index)
        #return int(np.linalg.norm(sub_points[f].coords - sub_points[t].coords) * 1000)    #returns the cost of the travel from f to t
        return int((distance_matrix[sub_points[f].idx][sub_points[t].idx]) *1000)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback) #tells it to use distance_callback for evaluating cost 
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        return None

    index = routing.Start(0)
    route = []
    while not routing.IsEnd(index):
        route.append(sub_points[manager.IndexToNode(index)])
        index = solution.Value(routing.NextVar(index))
    route.append(BASE)
    return route

# =========================
# MISSION EVALUATION
# =========================

def mission_energy(waypoints:tuple):
    if waypoints == []:     #no point of going to nothing (and generates errors)
        return None, []
    
    route = breadth_first(waypoints,BASE)
    if route is None:
        return None, None

    energy = route_energy(route)
    return energy, route

# =========================
# SPLIT SEARCH
# =========================

all_waypoints = waypoints

best_single = mission_energy(all_waypoints)

best_split_energy = float("inf")
best_split = None

print("-------\nstarting split search...\n-------")
#split seach only splits the payload in two groups for now
iteration = 0
for r in range(1, len(all_waypoints)-1):                      #just a brute force to find lowest energy consumption. should be fine bc we only have 7 hospitals
    noBase = [point for point in all_waypoints if point != BASE] #we're removing the base to make combinations as it needs to be added in both routes later on, but as combinations are random, base could be added two both and we don't want it twice in any of the two combinations
    for combo in itertools.combinations(noBase, r):
        iteration += 1
        other = tuple(x for x in all_waypoints if x not in combo)    #base already included in allwaypoints     also, the tuple is needed otherwise you get an empty ther by the time you want to generate combo_new (dont ask me why, has smth to do with generators)   
        combo_new = tuple(x for x in all_waypoints if (x not in other or x == BASE))  #also adding base to combo (creating a new vraiable cuz you otherwise get a generator already executing error)
        #^[Note]: the position of base doesn't mater, solve_route knows to start at base and not just take the first element as startpoint^
        
        #print(f"[split search]\ncombo {tuple(combo)}\ncombo_new {tuple(combo_new)}\nother {tuple(other)}")
        combo_payload = sum(point.payload for point in combo_new)
        other_payload = sum(point.payload for point in other)
        if combo_payload > MAX_PAYLOAD or other_payload > MAX_PAYLOAD:
            #print(f"[green]info[/green] skipping following combinations: combo {combo_new} other {other} \n[red]reason[/red]:",end="")
            print(f"[red]payload too high:[/red] combo {combo_payload}, other {other_payload}\nmax payload: {MAX_PAYLOAD}")
            continue            #skips the calculations completely if the maximum payload is reached (you can't fly anyways)

        e1, r1 = mission_energy(combo_new)
        e2, r2 = mission_energy(other)

        #print(f"iteration [{iteration}]\ne1: {e1}, r1: {r1}\ne2: {e2}, r2: {r2}")

        if e1 is None or e2 is None:            ####
            continue

        total = e1 + e2

        print(f"iteration [{iteration}]  energy: {total/3600:.1f}")
        if total < best_split_energy:
            best_split_energy = total
            best_split = (combo_new, other, r1, r2)
            print(f"[red bold]new best split found!![/red bold]\n[yellow]best_split:[/yellow] {best_split}")

            best_split_iteration = iteration

# =========================
# REPORT
# =========================

print("===== SINGLE MISSION =====")
if best_single[0] is not None:
    single_energy = best_single[0]
    print(f"Energy: {single_energy/3600:.1f} Wh")

    if single_energy > BATTERY_ENERGY * (1 - SAFETY_RESERVE):
        print("❌ Not feasible")
    else:
        print("✅ Feasible")

print("\n===== BEST 2-MISSION SPLIT =====")
if best_split:
    print("best split iteration: ", best_split_iteration)
    print("Group 1:", list(best_split[2]))
    print("Group 2:", list(best_split[3]))
    print(f"Total energy: {best_split_energy/3600:.1f} Wh")
