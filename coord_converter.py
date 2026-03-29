#https://chatgpt.com/share/69b40988-03a8-8013-bdfa-5801a934e8ad

import numpy as np
from pointlib import loadWaypoints

R = 6378137  # Earth radius (meters)

def gps_to_xy(lat, lon, lat0, lon0):
    x = np.radians(lon - lon0) * R * np.cos(np.radians(lat0))
    y = np.radians(lat - lat0) * R
    return np.array([x, y])

def xy_to_gps(x, y, lat0, lon0):
    lat = lat0 + np.degrees(y / R)
    lon = lon0 + np.degrees(x / (R * np.cos(np.radians(lat0))))
    return lat, lon

# Field reference points
A = (50.940388888889, 4.2105)   
B = (50.94108333333, 4.2105555555556)


# Brussels reference points
C = (50.85424625874742, 4.360304587589659)  #saint jean, real coords
D = (50.786195911015625, 4.366736317583127) #epsylon


# convert to local meters
A_xy = gps_to_xy(*A, *A)
B_xy = gps_to_xy(*B, *A)
C_xy = gps_to_xy(*C, *C)
D_xy = gps_to_xy(*D, *C)

v1 = B_xy - A_xy
v2 = D_xy - C_xy

scale = np.linalg.norm(v2) / np.linalg.norm(v1)
theta = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

Rmat = scale * np.array([
    [np.cos(theta), -np.sin(theta)],
    [np.sin(theta),  np.cos(theta)]
])

def transform(lat, lon):
    p = gps_to_xy(lat, lon, *A)
    p2 = Rmat @ p + C_xy
    return xy_to_gps(p2[0], p2[1], *C)

def transform_list(coords):
    newlist = []
    for coord in coords:
        new_coord = transform(coord[0],coord[1])
        newlist.append([float(new_coord[0]),float(new_coord[1])])



    return newlist
    
print(transform_list([[50.9405, 4.21039]]))

"""
waypoints, zones, _ = loadWaypoints("waypoints.json")

print(f"Waypoints\n-------------------------------\n")
names = []
points = []
for point in waypoints:
    names.append(point.name)
    points.append((point.lat, point.lon))

points = transform_list(points)

for i in range(len(points)):
    print(f"{names[i]}:  {points[i]}")

print(f"Zones\n-------------------------------\n")

for zone in zones:
    bounds = []
    for point in zone.bounds:
        bounds.append([point.lat, point.lon])
    print(f" {zone.name}: {transform_list(bounds)}", end="\n\n")"""
