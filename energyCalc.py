import math

CD = 1
RHO = 1.225
KANTELHOEK = 20
A = 0.05

MAXLIFT = 7.87696893

def lift_vert(mass):
    return mass*9.81

def a_hor(mass):
    return (MAXLIFT*math.sin(math.radians(KANTELHOEK)))/(mass)

def a_vert(mass):
    return ((MAXLIFT*4)-(lift_vert(mass)))/mass

def v_hor(mass):
    return math.sqrt((2*(mass)*math.tan(math.radians(KANTELHOEK)))/(CD*RHO*A))

def v_vert(mass):
    return math.sqrt(((2*(((MAXLIFT*4))-(lift_vert(mass))))/(CD*RHO*A)))

def travel_time(distance, v_max, a, d):
    """
    Bereken tijd voor een beweging met:
    afstand, topsnelheid, versnelling en vertraging
    """

    # afstand nodig voor versnellen en vertragen
    s_acc = v_max**2 / (2*a)
    s_dec = v_max**2 / (2*d)

    # geval 1: topsnelheid wordt bereikt
    if distance >= s_acc + s_dec:

        t_acc = v_max / a
        t_dec = v_max / d

        s_const = distance - s_acc - s_dec
        t_const = s_const / v_max

        return t_acc + t_const + t_dec

    # geval 2: topsnelheid wordt niet bereikt
    else:

        v_peak = math.sqrt(2*distance / (1/a + 1/d))

        t_acc = v_peak / a
        t_dec = v_peak / d

        return t_acc + t_dec


def drone_mission_time(
        D_h, v_h, a_h, d_h,
        D_v, v_v, a_v, d_v):

    # horizontale vlucht
    T_horizontal = travel_time(D_h, v_h, a_h, d_h)

    # dalen
    T_down = travel_time(D_v, v_v, a_v, d_v)

    # stijgen (zelfde parameters)
    T_up = travel_time(D_v, v_v, a_v, d_v)

    # totale tijd
    T_total = T_horizontal + T_down + T_up

    return T_horizontal, T_down, T_up, T_total

if __name__ == "__main__":
    # voorbeeld parameters
    D_h = 500      # horizontale afstand (m)
    v_h = 20       # horizontale topsnelheid (m/s)
    a_h = 4        # horizontale versnelling (m/s²)
    d_h = 4        # horizontale vertraging (m/s²)

    D_v = 100      # verticale afstand (m)
    v_v = 5        # verticale topsnelheid (m/s)
    a_v = 2        # verticale versnelling (m/s²)
    d_v = 2        # verticale vertraging (m/s²)


    Th, Td, Tu, Ttot = drone_mission_time(
        D_h, v_h, a_h, d_h,
        D_v, v_v, a_v, d_v
    )

    print("Horizontale tijd:", Th, "s")
    print("Tijd dalen:", Td, "s")
    print("Tijd stijgen:", Tu, "s")
    print("Totale tijd:", Ttot, "s")