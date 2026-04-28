import math
import heapq
import matplotlib.pyplot as plt
import json
from rich import print
import sys
import settings


def loadWaypoints(path, general_margin = 0):
    with open(path,'r') as file:
        dump = json.load(file)

        waypoints = dump["Waypoints"]
        pointlist = []
        bases = [waypoints[idx] for idx in waypoints if waypoints[idx]["type"]=="base"]     #should be only one
        if len(bases) >= 1:
            settings.ORIGIN = bases[0]["position"]
        for idx in waypoints:
            coord1 = waypoints[idx]["position"][0]
            coord2 = waypoints[idx]["position"][1]
            name = waypoints[idx]["name"]
            payload = waypoints[idx]["payload"]
            point_type = waypoints[idx]["type"]
            
            point = WayPoint(coord1, coord2, payload, name=name, idx=int(idx), origin_lat=settings.ORIGIN[0], origin_lon=settings.ORIGIN[1])
            if point_type == "base":
                base = point

            pointlist.append(point)

        noFlyZones = dump["NoFlyZones"]
        zones = []
        for idx in noFlyZones:
            if noFlyZones[idx]["ignore"]:
                continue
            bounds_list = noFlyZones[idx]["bounds"]
            bounds = []
            for point in bounds_list:
                bounds.append(Point(point[0],point[1],origin_lat=settings.ORIGIN[0], origin_lon=settings.ORIGIN[1]))
            name = noFlyZones[idx]["name"]
            margin = noFlyZones[idx].get("margin", general_margin) #if there's no "margin" key the general value applies
            if "margin" in noFlyZones[idx]:
                fixedmargin = True
            else:
                fixedmargin = False
            zones.append(NoFlyZone(bounds,idx, name, margin, fixedmargin, settings.ORIGIN[0], settings.ORIGIN[1]))
        
        

    return pointlist, zones, base

def loadsettings(path):
    with open(path,'r') as file:
        dump = json.load(file)
    
    return dump["settings"]



def orientation(a, b, c):
    val = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
    if abs(val) < 1e-9:
        return 0  # collinear
    return 1 if val > 0 else 2  # 1 = clockwise, 2 = counterclockwise


def on_segment(a, b, c):
    return (min(a.x, c.x) - 1e-9 <= b.x <= max(a.x, c.x) + 1e-9 and
            min(a.y, c.y) - 1e-9 <= b.y <= max(a.y, c.y) + 1e-9)


def segments_intersect(A, B, C, D):
    # --- ignore shared endpoints (CRUCIAL for visibility graphs)
    if A is C or A is D or B is C or B is D:
        return False

    o1 = orientation(A, B, C)
    o2 = orientation(A, B, D)
    o3 = orientation(C, D, A)
    o4 = orientation(C, D, B)

    # general case
    if o1 != o2 and o3 != o4:
        return True

    # special collinear cases
    if o1 == 0 and on_segment(A, C, B): return True
    if o2 == 0 and on_segment(A, D, B): return True
    if o3 == 0 and on_segment(C, A, D): return True
    if o4 == 0 and on_segment(C, B, D): return True

    return False

def collect_nodes(start, end, noflyzones):
    nodes = [start, end]
    for zone in noflyzones:
        nodes.extend(zone.bounds)
    return nodes

def visible(p1, p2, noflyzones):
    mid = Point((p1.x + p2.x)/2, (p1.y + p2.y)/2, "xy")

    for zone in noflyzones:
        hit, _, _ = zone.intersects_segment(p1, p2)
        if hit:
            return False

        #block if segment goes through interior
        if point_in_polygon(mid, zone.bounds):
            return False

    return True

def build_visibility_graph(nodes, noflyzones):
    graph = {node: [] for node in nodes}

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a = nodes[i]
            b = nodes[j]

            if visible(a, b, noflyzones):
                dist = a.distance_to(b)
                graph[a].append((b, dist))
                graph[b].append((a, dist))

    return graph

def shortest_path(graph, start, goal):
    pq = [(0, id(start), start)]
    dist = {start: 0}
    prev = {}

    while pq:
        cur_dist, _, node = heapq.heappop(pq)

        if node == goal:
            break

        for neigh, weight in graph[node]:
            new_dist = cur_dist + weight
            if neigh not in dist or new_dist < dist[neigh]:
                dist[neigh] = new_dist
                prev[neigh] = node
                heapq.heappush(pq, (new_dist, id(neigh), neigh))

    # reconstruct path
    try:
        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = prev[cur]
        path.append(start)
        path.reverse()
    except KeyError as e:
        print(f"\nGot a keyerror while building visibility graph. It's most likely due to a waypoint being inside a noflyzone. Try removing zones or reduce their margin around the following point:\n{e}")
        #exit()
    return path

def normalize(x, y):
    l = math.hypot(x, y)
    if l == 0:
        return 0, 0
    return x / l, y / l

def left_normal(x, y):
    return -y, x

def is_ccw(bounds):
    area = 0
    for i in range(len(bounds)):
        x1, y1 = bounds[i].coords
        x2, y2 = bounds[(i + 1) % len(bounds)].coords
        area += (x2 - x1) * (y2 + y1)
    return area < 0

def point_in_polygon(p, polygon):
    inside = False
    n = len(polygon)

    for i in range(n):
        a = polygon[i]
        b = polygon[(i + 1) % n]

        if ((a.y > p.y) != (b.y > p.y) and
            p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y + 1e-12) + a.x):
            inside = not inside

    return inside

def plot_scene(start, goal, noflyzones, link=None, show_graph=False, graph=None):
    plt.figure(figsize=(6,6))

    # --- draw no-fly zones ---
    for zone in noflyzones:
        xs = [p.x for p in zone.bounds] + [zone.bounds[0].x]
        ys = [p.y for p in zone.bounds] + [zone.bounds[0].y]
        plt.fill(xs, ys, label="noFlyZone")

    # --- draw visibility graph (optional) ---
    if show_graph and graph is not None:
        for node, edges in graph.items():
            for neigh, _ in edges:
                plt.plot([node.x, neigh.x], [node.y, neigh.y], linewidth=0.5, color="gray", label="Vis. graph")

    # --- draw path ---
    if link is not None:
        xs = [p.x for p in link.path]
        ys = [p.y for p in link.path]
        plt.plot(xs, ys, linewidth=3, color="green", label="Path")

    # --- draw start/goal ---
    plt.scatter([start.x], [start.y], s=100)
    plt.scatter([goal.x], [goal.y], s=100)

    plt.axis("equal")
    
    handles, labels = plt.gca().get_legend_handles_labels()
    newLabels, newHandles = [], []
    for handle, label in zip(handles, labels):
        if label not in newLabels or label == "noFlyZone":
            newLabels.append(label)
            newHandles.append(handle)

    plt.legend(newHandles, newLabels)
    plt.grid(True)
    plt.show()



class Point:
    EARTH_RADIUS = 6371000  # meters

    def __init__(self, coord1, coord2, coord_type = "gps", origin_lat = settings.ORIGIN[0], origin_lon = settings.ORIGIN[1], idx:int = -1):		
        #origin_lat, origin_lon: reference point in degrees
        self.origin_lat = math.radians(origin_lat)
        self.origin_lon = math.radians(origin_lon)
        self.cos_lat = math.cos(self.origin_lat)
        self.preferred_coord = coord_type
                
        self.setcoords(coord1, coord2, coord_type)
        
        self.idx = idx
    def setcoords(self, coord1, coord2, coord_type = "gps"):
        if coord_type == "gps":
            self.x, self.y = self.to_xy(coord1, coord2)
            self.lat, self.lon = coord1, coord2
        elif coord_type == "xy": 
            self.x, self.y = coord1, coord2
            self.lat, self.lon = self.to_gps(coord1, coord2)
        else: 
            raise NotImplementedError()
    def to_xy(self, lat, lon):
        #Convert latitude/longitude to x/y in meters
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        dlon = lon_rad - self.origin_lon
        dlat = lat_rad - self.origin_lat

        x = dlon * self.EARTH_RADIUS * self.cos_lat
        y = dlat * self.EARTH_RADIUS

        return x, y

    def to_gps(self, x, y):
        #Convert local x/y (meters) back to latitude/longitude
        lat_rad = y / self.EARTH_RADIUS + self.origin_lat
        lon_rad = x / (self.EARTH_RADIUS * self.cos_lat) + self.origin_lon

        return math.degrees(lat_rad), math.degrees(lon_rad)
    
    def distance_to(self, point):
        return math.sqrt((point.x-self.x)**2+(point.y-self.y)**2)
    
    def __str__(self):
        return f"Point @ x = {self.x:.3f} y = {self.y:.3f}"
    
    def __repr__(self):
        return self.__str__()
    
    """def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)"""

    """def __hash__(self):
        return hash((round(self.x, 6), round(self.y, 6)))"""
    
    @property
    def coords(self):
        return self.x, self.y
    

class WayPoint(Point):
    def __init__(self, coord1, coord2, payload = 0, coord_type = "gps", name="Point",  origin_lat = settings.ORIGIN[0], origin_lon = settings.ORIGIN[1], idx:int = -1):
        super().__init__(coord1, coord2, coord_type, origin_lat, origin_lon, idx)

        self.name = name
        self.payload = payload
    
    def __str__(self):
        return f"Waypoint \"{self.name}\" @ x = {self.x:.3f}, y = {self.y:.3f}"

class NoFlyZone:
    def __init__(self, bounds: list, idx = -1, name = "no fly zone", margin = 0, fixedmargin=False,  origin_lat=50.9405, origin_lon=4.21039):
        if is_ccw(bounds):              #checkt de volgorde van de bound-punten van de no fly zone. indien ze in de slechte volgorde worden ingegeven kan het onflaten mislopen
            bounds = list(reversed(bounds))
        self.bounds = bounds        #list with the coordinates of the corners in order
        self.idx = idx
        self.name = name
        self.margin = margin
        
        if fixedmargin:
            self.fixedmargin = True
        else:
            self.fixedmargin = False
        
    #vv niet de beste manier ma bon het werkt vv
    @property
    def margin(self):
         return self.margin_
    
    @margin.setter
    def margin(self, arg):
        self.margin_ = arg
        if arg != 0:
            self.margin_zone = self.inflated(self.margin)
        else:
            self.margin_zone = self
    
    def intersects_segment(self, p1:Point, p2:Point):
        n = len(self.bounds)
        for i in range(n):
            a = self.bounds[i]
            b = self.bounds[(i + 1) % n]
            if segments_intersect(p1, p2, a, b):
                return True, a, b
        return False, None, None
    
    def inflated(self, margin):
        n = len(self.bounds)
        new_bounds = []

        for i in range(n):
            p_prev = self.bounds[(i - 1) % n]
            p_curr = self.bounds[i]
            p_next = self.bounds[(i + 1) % n]

            # edge vectors
            v1x = p_curr.x - p_prev.x
            v1y = p_curr.y - p_prev.y
            v2x = p_next.x - p_curr.x
            v2y = p_next.y - p_curr.y

            # normals (pointing outward for CCW polygon)
            n1x, n1y = normalize(*left_normal(v1x, v1y))
            n2x, n2y = normalize(*left_normal(v2x, v2y))

            # bisector direction
            bisx = n1x + n2x
            bisy = n1y + n2y
            bisx, bisy = normalize(bisx, bisy)

            # angle correction (important!)
            dot = n1x * bisx + n1y * bisy
            if abs(dot) < 1e-6:
                scale = margin
            else:
                scale = margin / dot

            new_bounds.append(
                Point(
                    p_curr.x + bisx * scale,
                    p_curr.y + bisy * scale,
                    "xy"
                )
            )

        return NoFlyZone(new_bounds)
    
    def __str__(self):
        lst = []
        for i in self.bounds:
            lst.append(str(i))
        return f"noFlyZone: {self.name} with bounds: {lst}"
    def __repr__(self):
        return self.__str__()

class Link:
    def __init__(self, start: WayPoint, end: WayPoint, noflyzones:list=None):
        if not noflyzones:
            self.path = [start, end]
            return
        
        noflyzones = [zone.margin_zone for zone in noflyzones] #makes new, slightly bigger noflyzones so you don't touch the corners of the zone

        #for zone in noflyzones:
        #        print(zone)

        nodes = collect_nodes(start, end, noflyzones)
        graph = build_visibility_graph(nodes, noflyzones)
        self.path = shortest_path(graph, start, end)

        if __name__ == "__main__":
            plot_scene(start, goal, noflyzones, link=self, show_graph=True, graph=graph)
            ...

    def length(self):
        i=0
        dist = 0
        while i < len(self.path)-1:
            dist += self.path[i].distance_to(self.path[i+1])
            i += 1
        return dist


if __name__ == "__main__":

    noFlyZones = [
        NoFlyZone([
            Point(10,20,"xy"),
            Point(30,15,"xy"),
            Point(20,5,"xy"),
            Point(9,8,"xy")
        ]),
        NoFlyZone([
            Point(5,7,"xy"),
            Point(25,7,"xy"),
            Point(25,3,"xy"),
            Point(5,3,"xy")
        ])
    ]

    start = WayPoint(16,30,coord_type="xy")
    goal = WayPoint(15,-6,coord_type="xy")

    a = Link(start, goal, noflyzones=noFlyZones)

    for p in a.path:
        print(p)

    """from UI_ressources import *
    app = QApplication(sys.argv)

    view = MapView()

    draw_link(view.scene_,a)
    draw_zone(view.scene_,noFlyZones[1])

    view.show()

    sys.exit(app.exec())"""