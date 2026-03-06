import numpy as np
import itertools
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from pointlib import loadWaypoints, WayPoint, Link, NoFlyZone
from rich import print

# =========================
# USER PARAMETERS
# =========================

EMPTY_MASS = 1.5691  # kg
CRUISE_SPEED = 5.736  # m/s
BATTERY_ENERGY = 74 * 3600  # Joules (for a 74 wh battery)

# --- Flight profile ---
CRUISE_ALTITUDE = 30.0
CLIMB_RATE = 9.2242            #????
DESCENT_RATE = 2.0          #????
SAFETY_RESERVE = 0.15

# --- Power model ---
A = 120.0
B = 50.0

# --- Loading Waypoints and selecting BASE ---
waypoints = loadWaypoints("waypoints.json")
BASE = waypoints[0]

# =========================
# ENERGY MODEL (chatgpt for now, to be changed evntually)
# =========================

def power_required(mass):
    return A * (mass ** 1.5) + B

def climb_energy(mass):
    t = CRUISE_ALTITUDE / CLIMB_RATE
    return power_required(mass) * t

def descent_energy(mass):
    t = CRUISE_ALTITUDE / DESCENT_RATE
    return 0.5 * power_required(mass) * t  # in general, the descend demands 30–70% of hover power, so 50% is average. we could measure that (though i dont think its really that impactful)

def energy_for_leg(distance, mass):
    time = distance / CRUISE_SPEED
    return power_required(mass) * time

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

def route_energy(route, waypoints):
    #print(f"[route_energy] Route: {route} waypoints: {waypoints}")
    payload_subset = [point.payload for point in waypoints]     #the total payload list needed for this route
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
        return None, None
    
    route = solve_route(waypoints,BASE)
    if route is None:
        return None, None

    energy = route_energy(route, waypoints)
    return energy, route

# =========================
# SPLIT SEARCH
# =========================

all_waypoints = waypoints

best_single = mission_energy(all_waypoints)

best_split_energy = float("inf")
best_split = None

print("-------\nstarting split search...\n-------")

iteration = 0
for r in range(1, len(all_waypoints)-1):                      #just a brute force to find lowest energy consumption. should be fine bc we only have 7 hospitals
    noBase = [point for point in all_waypoints if point != BASE] #we're removing the base to make combinations as it needs to be added in both routes later on
    for combo in itertools.combinations(noBase, r):
        iteration += 1
        other = tuple(x for x in all_waypoints if x not in combo)    #base already included in allwaypoints     also, the tuple is needed, otherwise you get an empty ther by the time you want to generate combo_new (dont ask me why, has smth to do with generators)   
        combo_new = tuple(x for x in all_waypoints if (x not in other or x == BASE))  #also adding base to combo (creating a new vraiable cuz you otherwise get a generator already executing error)
        #^[Note]: the position of base doesn't mater, solve_route knows to start at base and not just take the first element as startpoint^
        
        #print(f"[split search]\ncombo {tuple(combo)}\ncombo_new {tuple(combo_new)}\nother {tuple(other)}")

        e1, r1 = mission_energy(combo_new)
        e2, r2 = mission_energy(other)

        print(f"iteration [{iteration}]\ne1: {e1}, r1: {r1}\ne2: {e2}, r2: {r2}")

        if e1 is None or e2 is None:            ####
            continue

        total = e1 + e2

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