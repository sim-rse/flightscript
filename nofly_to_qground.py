import json

# files
WAYPOINTS_FILE = "waypoints.json"
PLAN_FILE = "C:/Users/simon/Documents/QGroundControl/Missions/flight1.plan"
OUTPUT_FILE = "C:/Users/simon/Documents/QGroundControl/Missions/flight1.plan"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def convert_noflyzones_to_polygons(noflyzones:dict):
    polygons = []

    for key, zone in noflyzones.items():
        bounds = zone.get("bounds", [])
        ignore = zone.get("ignore", False)
        if ignore:
            continue
        polygon = {
            "inclusion": False,
            "version": 1,
            "polygon": [
                [coord[0],
                 coord[1]
                ]
                for coord in bounds
            ]
        }

        polygons.append(polygon)

    return polygons

def main():
    waypoints_data = load_json(WAYPOINTS_FILE)
    plan_data = load_json(PLAN_FILE)

    noflyzones = waypoints_data.get("NoFlyZones", {})
    polygons = convert_noflyzones_to_polygons(noflyzones)

    # Ensure structure exists
    if "geoFence" not in plan_data:
        plan_data["geoFence"] = {}

    # Replace or create polygons
    plan_data["geoFence"]["polygons"] = polygons

    save_json(plan_data, OUTPUT_FILE)
    print(f"Updated plan saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()