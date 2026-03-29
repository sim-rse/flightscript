import math
import settings

# CONSTANTEN
g = 9.81

#vv unused vv
CD = 1.0
RHO = 1.225
A = 0.05

KANTELHOEK = 20  # graden

MAXLIFT = 7.87696893  # per motor
MOTORS = 4


# --- BASISKRACHTEN ---

def lift_vert(mass):
    return mass * g


def total_thrust():
    return settings.MAXLIFT * settings.MOTORS


# --- VERSNELLINGEN ---

def a_hor(mass):
    thrust_h = total_thrust() * math.sin(math.radians(settings.KANTELHOEK))
    return thrust_h / mass


def a_vert(mass):
    thrust = total_thrust()
    return (thrust - lift_vert(mass)) / mass


# --- MAXIMALE SNELHEDEN ---

def v_hor(mass):
    thrust_h = total_thrust() * math.sin(math.radians(settings.KANTELHOEK))
    return math.sqrt((2 * thrust_h) / (settings.CD * settings.RHO * settings.A))


def v_vert(mass):
    thrust = total_thrust()
    F = thrust - lift_vert(mass)

    if F <= 0:
        return 0

    return math.sqrt((2 * F) / (settings.CD * settings.RHO * settings.A))


# --- TIJD BEREKENING ---

def travel_time(distance, vmax, acceleration):

    s_min = vmax**2 / acceleration

    if distance > s_min:

        t_acc = vmax / acceleration
        t_dec = vmax / acceleration

        s_cruise = distance - s_min
        t_cruise = s_cruise / vmax

        total_time = t_acc + t_cruise + t_dec

    else:

        v_peak = math.sqrt(acceleration * distance)
        t_acc = v_peak / acceleration

        total_time = 2 * t_acc

    return total_time


# --- MISSIE TIJD ---

def drone_mission_time(D_h, v_h, a_h, D_v, v_v, a_v):

    T_horizontal = travel_time(D_h, v_h, a_h)
    T_up = travel_time(D_v, v_v, a_v)
    T_down = travel_time(D_v, v_v, a_v)

    T_total = T_horizontal + T_up + T_down

    return T_horizontal, T_up, T_down, T_total


# --- TEST ---

if __name__ == "__main__":

    mass = 1.5691

    print(f"Horizontal top speed:     {v_hor(mass):.3f} m/s ({v_hor(mass)*3.6:.3f} km/h)")
    print(f"Horizontal acceleration:  {a_hor(mass):.3f} m/s²")
    print(f"Vertical top speed:       {v_vert(mass):.3f} m/s ({v_vert(mass)*3.6:.3f} km/h)")
    print(f"Vertical acceleration:    {a_vert(mass):.3f} m/s²")

    print()

    D_h = 20
    D_v = 5

    Th, Tu, Td, Ttot = drone_mission_time(
        D_h, v_hor(mass), a_hor(mass),
        D_v, v_vert(mass), a_vert(mass)
    )

    print("Horizontale tijd:", Th, "s")
    print("Tijd stijgen:", Tu, "s")
    print("Tijd dalen:", Td, "s")
    print("Totale tijd:", Ttot, "s")