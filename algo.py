import numpy as np
import itertools
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from pointlib import loadWaypoints, WayPoint, Link, NoFlyZone
from rich import print
from energyCalc import *
import settings
# =========================
# USER PARAMETERS
# =========================
if __name__ == "__main__":
    EMPTY_MASS = 1.562  # kg
    BATTERY_ENERGY = 74 * 3600  #multiply Wh by 3600 to get the energy in Joules
    MAX_PAYLOAD = 0.6

    # --- Flight profile ---
    CRUISE_ALTITUDE = 30
    SAFETY_RESERVE = 0.15

    # --- needed for acceleration calculations etc in energyCalc.py---
    CD = 1
    RHO = 1.225
    KANTELHOEK = 20
    A = 0.05

    MAXLIFT = 7.87696893

# --- Loading Waypoints and selecting BASE ---
waypoints, noflyzones, BASE = loadWaypoints("waypoints.json")       #wordt enkel gebruikt indien je algo.py runt voor het pad van het GUI programma moet je in algo_gui.py de pad veranderen!

# =========================
# ENERGY MODEL
# =========================

def power_required(lift):
    return 1.231073846*(lift**2) + 7.431724825*lift - 2.405185698       #quadratic regression of power in function of the lift (from experimental results)
    #return A * (mass ** 1.5) + B

def climb_energy(mass):    
    a_v, v_v = a_vert(mass), v_vert(mass)
    d_v = a_v

    T_up = travel_time(settings.CRUISE_ALTITUDE, v_v, a_v)

    lift = (a_v+d_v)*mass
    #t = settings.CRUISE_ALTITUDE / CLIMB_RATE
    return power_required(lift) * T_up

def descent_energy(mass):
    a_v, v_v = a_vert(mass), v_vert(mass)
    d_v = a_v
    T_down = travel_time(settings.CRUISE_ALTITUDE, v_v, a_v)

    lift = (a_v+d_v)*mass
    #t = settings.CRUISE_ALTITUDE / DESCENT_RATE
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
def get_links_and_dist(points, noflyzones = []):
    n = len(points)
    links = np.full((n, n), None, dtype=object) #create empty matrix with only "None"'s

    distances = np.zeros((n, n))

    for i in range(n):
        #only iterating for the upper triangle of the matrix (and doing the lower at the same time)
        for j in range(i+1,n):      #i+1 for skipping the diagonal
            value = Link(points[i],points[j], noflyzones=noflyzones)
            dist = value.length()

            links[i][j] = value
            links[j][i] = value

            distances[i,j] = dist
            distances[j,i] = dist

    return links, distances

#print(f"Distance matrix: {distance_matrix}")
# =========================
# ROUTE ENERGY
# =========================

def route_energy(route, return_partial_energies = False):
    #print(f"[route_energy] Route: {route} waypoints: {waypoints}")
    payload_subset = [point.payload for point in route]     #the total payload list needed for this route
    remaining_payload = sum(payload_subset)
    total_mass = settings.EMPTY_MASS + remaining_payload

    if return_partial_energies:
        partial = []

    energy = 0.0

    # takeoff climb
    energy += climb_energy(total_mass)

    for i in range(len(route) - 1):
        a:WayPoint = route[i] 
        b:WayPoint = route[i+1]
        #print(f"a :{a}, b: {b}\nindex a :{a.idx} index b: {b.idx}\ntype: {type(a.idx)}")
        #print(f"distance matrix size: {len(distance_matrix)}\na: {a.idx} b: {b.idx}")
        d = distance_matrix[a.idx, b.idx]

        #travelling to waypoint
        energy += energy_for_leg(d, total_mass)

        # payload drop
        energy += descent_energy(total_mass)

        if return_partial_energies:
            partial_energy = climb_energy(total_mass) + energy_for_leg(d,total_mass) + descent_energy(total_mass)
            partial.append((f"{a.name} - {b.name}", partial_energy))

        remaining_payload -= b.payload              #the last waypoint is back to the origin, but the payload there is 0 so no problem
        total_mass = settings.EMPTY_MASS + remaining_payload
        
        if i+1 != len(route):       #won't take off at the last step
            #take off again
            energy += climb_energy(total_mass)
    if return_partial_energies:
        return energy, partial
    return energy

# =========================
# best path
# =========================

def breadth_first(waypoints:list, startpoint):
    remaining = [point for point in waypoints if not point == startpoint]
    energy = float('inf')
    route = None
    #print(f"getting all permutations of {remaining}")
    for combination in itertools.permutations(remaining):
        new_route = [startpoint]+list(combination)+[startpoint]
        new_energy = route_energy(new_route)
        if new_energy < energy:
            route = new_route
            energy = new_energy
            #print(f"[[red bold]![/red bold]] found new best route: {route}")
    return route


# =========================
# MISSION EVALUATION
# =========================

def mission_energy(waypoints:tuple, BASE):
    if waypoints == []:     #no point of going to nothing (and generates errors)
        return None, []
    
    route = breadth_first(waypoints, BASE)
    if route is None:
        return None, []

    energy = route_energy(route)
    return energy, route


def print_partial_energies(route, title:str = None):
    if type(title) is str:
        print("=========",title.upper(),"=========")

    print('----------partial energies----------')
    energy, partial = route_energy(route,True)
    for name, energy in partial:
        print(f"Energy for link \"{name}\":  {energy/3600:.3f} Wh")
    print('------------------------------------')
    print(f"Total Energy: {energy/3600:.1f} Wh")

def main(all_waypoints = waypoints, noflyzones_ = noflyzones, BASE = BASE):

    """config = {
    "EMPTY_MASS": settings.EMPTY_MASS,
    "BATTERY_ENERGY": BATTERY_ENERGY,
    "MAX_PAYLOAD": MAX_PAYLOAD,
    "CRUISE_ALTITUDE": CRUISE_ALTITUDE,
    "SAFETY_RESERVE": SAFETY_RESERVE,
    "CD": CD,
    "RHO": RHO,
    "KANTELHOEK": KANTELHOEK,
    "A": A,
    "MAXLIFT": MAXLIFT
    }"""

    global links, distance_matrix
    links, distance_matrix = get_links_and_dist(all_waypoints, noflyzones_)

    # =========================
    # SINGLE SEARCH
    # =========================
    single_energy, single_route = mission_energy(all_waypoints, BASE)

    # =========================
    # SPLIT SEARCH
    # =========================
    #print("-------\nstarting split search...\n-------")

    best_split_energy = float("inf")
    best_split = None

    #split seach only splits the payload in two groups for now
    iteration = 0

    e1, r1 = 0, []
    e2, r2 = 0,[]
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
            if combo_payload > settings.MAX_PAYLOAD or other_payload > settings.MAX_PAYLOAD:
                #print(f"[green]info[/green] skipping following combinations: combo {combo_new} other {other} \n[red]reason[/red]:",end="")
                #print(f"[red]payload too high:[/red] combo {combo_payload}, other {other_payload}\nmax payload: {settings.MAX_PAYLOAD}")
                continue            #skips the calculations completely if the maximum payload is reached (you can't fly anyways)

            e1, r1 = mission_energy(combo_new, BASE)
            e2, r2 = mission_energy(other, BASE)

            #print(f"iteration [{iteration}]\ne1: {e1}, r1: {r1}\ne2: {e2}, r2: {r2}")

            if e1 is None or e2 is None:            ####
                continue

            total = e1 + e2

            #print(f"iteration [{iteration}]  energy: {total/3600:.1f}")
            if total < best_split_energy:
                best_split_energy = total
                best_split = (combo_new, other, r1, r2)
                #print(f"[red bold]new best split found!![/red bold]\n[yellow]best_split:[/yellow] {best_split}")

                best_split_iteration = iteration

    # =========================
    # REPORT
    # =========================

    print("===== SINGLE MISSION =====")
    if single_route is not None:
        print(f"Best route: {list(single_route)}")
        print_partial_energies(single_route)

        if single_energy > settings.BATTERY_ENERGY * (1 - settings.SAFETY_RESERVE):
            print("❌ Not feasible")
        else:
            print("✅ Feasible")

    print("\n===== BEST 2-MISSION SPLIT =====")
    if best_split:
        print("best split iteration: ", best_split_iteration)
        print("Group 1:", list(best_split[2]))
        print("Group 2:", list(best_split[3]))

        print_partial_energies(best_split[2], "split 1")
        print_partial_energies(best_split[3], "split 2")

        print(f"Total energy: {best_split_energy/3600:.1f} Wh")


    

    def to_links(route):
        route_links = []
        for i in range(len(route)-1):
            route_links.append(links[route[i].idx, route[i+1].idx])
        return route_links
    return  to_links(single_route), to_links(r1), to_links(r2)

if __name__ == "__main__":
    main()
