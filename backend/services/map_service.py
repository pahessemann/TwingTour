import json
import math
import random

from backend.services.seed_service import CAPITAL_NODE_IDS, COORD_OFFSET_X, COORD_OFFSET_Y, COORD_SCALE_X, COORD_SCALE_Y, MAP_HEIGHT, MAP_WIDTH


ROUTE_CASE_KM = 100
ROUTE_CASE_COSTS = {
    "autoroute": {"fuel": 1, "coins": 9, "durability": 1},
    "nationale": {"fuel": 2, "coins": 0, "durability": 2},
    "departementale": {"fuel": 3, "coins": 0, "durability": 4},
}


def _node(row):
    data = dict(row)
    data["resource"] = json.loads(data.pop("resource_json") or "{}")
    data["is_capital"] = data["id"] in CAPITAL_NODE_IDS
    return data


def _road(row):
    return dict(row)


def _case_count(distance_km):
    return max(1, int(math.floor((distance_km / ROUTE_CASE_KM) + 0.5)))


def _case_feature(route_id, index, case_count):
    if index == 0 or index == case_count:
        return "city"
    rng = random.Random(f"{route_id}:{index}")
    if index % 5 == 0:
        return "bifurcation"
    roll = rng.randint(1, 100)
    if roll <= 16:
        return "bonus"
    if roll <= 30:
        return "malus"
    if roll <= 42:
        return "event"
    return "empty"


def _case_effect(feature):
    if feature == "bonus":
        return {"coins": 8, "fuel": 1, "durability": 2}
    if feature == "malus":
        return {"coins": -6, "fuel": -1, "durability": -4}
    if feature == "event":
        return {"xp": 5, "durability": -1}
    return {}


def _route_id(road):
    endpoints = sorted([road["from_node_id"], road["to_node_id"]])
    return f"r-{endpoints[0].lower()}-{endpoints[1].lower()}"


def _offset_point(from_node, to_node, index, case_count):
    ratio = index / case_count if case_count else 0
    x = from_node["x"] + (to_node["x"] - from_node["x"]) * ratio
    y = from_node["y"] + (to_node["y"] - from_node["y"]) * ratio
    return {
        "x": round(x),
        "y": round(y),
    }


def _route_from_road(road, nodes_by_id):
    road = dict(road)
    from_node = nodes_by_id[road["from_node_id"]]
    to_node = nodes_by_id[road["to_node_id"]]
    route_type = road["road_type"]
    case_count = _case_count(road["distance_km"])
    route_id = _route_id(road)
    costs = ROUTE_CASE_COSTS[route_type]
    cases = []
    for index in range(case_count + 1):
        point = _offset_point(from_node, to_node, index, case_count)
        feature = _case_feature(route_id, index, case_count)
        node_id = road["from_node_id"] if index == 0 else road["to_node_id"] if index == case_count else None
        cases.append(
            {
                "id": f"{route_id}:{index}",
                "route_id": route_id,
                "index": index,
                "node_id": node_id,
                "kind": feature,
                "x": point["x"],
                "y": point["y"],
                "effect": _case_effect(feature),
            }
        )
    return {
        "id": route_id,
        "road_id": road["id"],
        "variant": 0,
        "from_node_id": road["from_node_id"],
        "to_node_id": road["to_node_id"],
        "road_type": route_type,
        "case_count": case_count,
        "distance_km": case_count * ROUTE_CASE_KM,
        "cost_coins": costs["coins"] * case_count,
        "fuel_cost": costs["fuel"] * case_count,
        "durability_cost": costs["durability"] * case_count,
        "per_case": costs,
        "cases": cases,
    }


def get_board_routes(conn):
    nodes_by_id = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM map_nodes").fetchall()}
    routes = []
    for road in conn.execute("SELECT * FROM roads ORDER BY id").fetchall():
        routes.append(_route_from_road(road, nodes_by_id))
    return routes


def get_board_route(conn, route_id):
    for route in get_board_routes(conn):
        if route["id"] == route_id:
            return route
    return None


def get_board_routes_between(conn, a, b):
    return [
        route
        for route in get_board_routes(conn)
        if {route["from_node_id"], route["to_node_id"]} == {a, b}
    ]


def route_position(route, index):
    index = max(0, min(route["case_count"], int(index)))
    return route["cases"][index]


def get_map(conn):
    nodes = [_node(row) for row in conn.execute("SELECT * FROM map_nodes ORDER BY city").fetchall()]
    roads = [_road(row) for row in conn.execute("SELECT * FROM roads ORDER BY id").fetchall()]
    return {
        "width": MAP_WIDTH,
        "height": MAP_HEIGHT,
        "nodes": nodes,
        "roads": roads,
        "board_routes": get_board_routes(conn),
        "case_km": ROUTE_CASE_KM,
        "terrain_scale_x": COORD_SCALE_X,
        "terrain_scale_y": COORD_SCALE_Y,
        "terrain_offset_x": COORD_OFFSET_X,
        "terrain_offset_y": COORD_OFFSET_Y,
    }


def get_node(conn, node_id):
    row = conn.execute("SELECT * FROM map_nodes WHERE id = ?", (node_id,)).fetchone()
    return _node(row) if row else None


def get_road_between(conn, a, b):
    row = conn.execute(
        """
        SELECT * FROM roads
        WHERE (from_node_id = ? AND to_node_id = ?)
           OR (from_node_id = ? AND to_node_id = ?)
        """,
        (a, b, b, a),
    ).fetchone()
    return _road(row) if row else None
