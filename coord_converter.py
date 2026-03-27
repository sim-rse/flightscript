#https://chatgpt.com/share/69b40988-03a8-8013-bdfa-5801a934e8ad

import numpy as np

R = 6378137  # Earth radius (meters)

def gps_to_xy(lat, lon, lat0, lon0):
    x = np.radians(lon - lon0) * R * np.cos(np.radians(lat0))
    y = np.radians(lat - lat0) * R
    return np.array([x, y])

def xy_to_gps(x, y, lat0, lon0):
    lat = lat0 + np.degrees(y / R)
    lon = lon0 + np.degrees(x / (R * np.cos(np.radians(lat0))))
    return lat, lon

# Brussels reference points
A = (50.85424625874742, 4.360304587589659)  #saint jean, real coords
B = (50.786195911015625, 4.366736317583127) #epsylon

# Field reference points
C = (50.940388888889, 4.2105)   
D = (50.94108333333, 4.2105555555556)

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
print(transform_list([[50.8163917670418, 4.3757961513428265],[50.82042815131645, 4.373505032173581],[50.821263827175514, 4.369179116066654],[50.81771774832251, 4.371681712161571]]))