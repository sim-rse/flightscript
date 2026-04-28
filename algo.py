import numpy as np
import itertools
from pointlib import loadWaypoints, WayPoint, Link, NoFlyZone
from rich import print
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from energyCalc import *
import settings
import os

console = Console()
console.print("[bold]Drone route planner[/bold] - get the latest updates on", end=" ")
console.print("github", style="link https://github.com/sim-rse/flightscript/")
# =========================
# USER PARAMETERS (unused, see settings.py)
# =========================

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
waypoints, noflyzones, BASE = loadWaypoints("waypoints_BXL.json")       #wordt enkel gebruikt indien je algo.py runt voor het pad van het GUI programma moet je in algo_gui.py de pad veranderen!

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

# =========================
# RICH FANCY FUNCTIONS
# =========================
def cls():
    os.system('cls' if os.name=='nt' else 'clear')
    console.print("[bold]Drone route planner[/bold] - get the latest updates on", end=" ")
    console.print("github", style="link https://github.com/sim-rse/flightscript/")

def route_to_names(route):
    return " → ".join(point.name for point in route)


def energy_style(e_wh, max_energy_wh):
    ratio = e_wh / max_energy_wh

    if ratio < (1-settings.SAFETY_RESERVE):
        return "green"
    elif ratio <= 1.0:
        return "yellow"
    else:
        return "red"

def print_partial_energies(route, title: str = None):
    energy, partial = route_energy(route, True)

    max_energy_wh = settings.BATTERY_ENERGY / 3600

    table = Table(title=title or "Partial Energies")
    table.add_column("Section", style="cyan")
    table.add_column("Energy (Wh)", justify="right")

    total_energy = 0

    for name, e in partial:
        e_wh = e / 3600
        total_energy += e_wh

        style = energy_style(e_wh, max_energy_wh)
        table.add_row(name, f"[{style}]{e_wh:.2f}[/{style}]")

    table.add_section()

    total_style = energy_style(total_energy, max_energy_wh)
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold {total_style}]{total_energy:.2f}[/bold {total_style}]"
    )

    console.print(table)

def feasibility_text(energy):
    ratio = energy / settings.BATTERY_ENERGY

    if ratio < 1-settings.SAFETY_RESERVE:
        return "[bold green]✅ Safe[/bold green]"
    elif ratio <= 1.0:
        return "[bold yellow]⚠️ Close to limit[/bold yellow]"
    else:
        return "[bold red]❌ Not feasible[/bold red]"

def main(all_waypoints = waypoints, noflyzones_ = noflyzones, BASE = BASE):
    global links, distance_matrix
    links, distance_matrix = get_links_and_dist(all_waypoints, noflyzones_)

    # =========================
    # SINGLE SEARCH
    # =========================
    if settings.ROUTETYPE in ("single", "all"):
        single_energy, single_route = mission_energy(all_waypoints, BASE)
    else:
        single_energy, single_route = 0,[]

    # =========================
    # SPLIT SEARCH
    # =========================
    e1, r1 = 0, []
    e2, r2 = 0,[]
    if settings.ROUTETYPE in ("two", "all"):
        #print("-------\nstarting split search...\n-------")

        best_split_energy = float("inf")
        best_split = None

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

    #----------------------------------------------------------------------------------
    if settings.ROUTETYPE in ("single", "all"):
        console.print("\n[bold blue]===== SINGLE MISSION =====[/bold blue]")

        if single_route is not None:
            console.print(Panel(
                f"[bold]Best route:[/bold]\n{route_to_names(single_route)}",
                border_style="green"
            ))

            print_partial_energies(single_route)

            print(feasibility_text(single_energy))
    #----------------------------------------------------------------------------------
    if settings.ROUTETYPE in ("two", "all"):
        console.print("\n[bold blue]===== BEST 2-MISSION SPLIT =====[/bold blue]")
        if best_split:
            console.print(f"[dim]Best split found at iteration {best_split_iteration}[/dim]\n")

            console.print(Panel(
                f"[bold]Route 1:[/bold]\n{route_to_names(best_split[2])}",
                border_style="cyan"
            ))
            print_partial_energies(best_split[2], "Split 1")

            console.print(Panel(
                f"[bold]Route 2:[/bold]\n{route_to_names(best_split[3])}",
                border_style="cyan"
            ))
            print_partial_energies(best_split[3], "Split 2")

            console.print(f"\n[bold yellow]Total energy:[/bold yellow] {best_split_energy/3600:.1f} Wh")
        else: 
            print('No best split route found !')
    #----------------------------------------------------------------------------------

    def to_links(route):
        route_links = []
        for i in range(len(route)-1):
            route_links.append(links[route[i].idx, route[i+1].idx])
        return route_links
    
    return  to_links(single_route), to_links(r1), to_links(r2)

if __name__ == "__main__":
    main()
