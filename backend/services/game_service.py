import random

from backend.models.errors import ApiError
from backend.services.map_service import get_node, get_road_between
from backend.services.progression_service import get_progression, serialize_progression, sync_unlocks_and_achievements, update_progression


WEATHER_FUEL_COST = {
    "clear": 0,
    "rain": 2,
    "fog": 3,
    "snow": 5,
    "wind": 2,
    "heat": 2,
}
FUEL_CAPACITY_LITERS = 35


def _random_event(conn, road):
    return None


def _apply_node_resource(progress, node):
    resource = node["resource"]
    messages = []
    coins = 0
    fuel = progress["fuel"]
    repairs_needed = progress["repairs_needed"]

    if node["node_type"] == "station":
        fuel = max(fuel, int(resource.get("fuel", FUEL_CAPACITY_LITERS)))
        messages.append("Plein effectue a la station-service.")
    elif node["node_type"] == "garage":
        repair_cost = abs(int(resource.get("repair", -25)))
        if repairs_needed:
            repairs_needed = 0
            messages.append("Garage visite: la Twingo est reparee.")
        else:
            fuel = min(FUEL_CAPACITY_LITERS, fuel + 8)
            messages.append("Garage visite: petit check-up offert.")
    else:
        coin_delta = int(resource.get("coins", 0))
        fuel_delta = int(resource.get("fuel", 0))
        if coin_delta:
            messages.append("Ressource de partie ignoree hors session.")
        if fuel_delta:
            fuel = min(FUEL_CAPACITY_LITERS, fuel + fuel_delta)
            messages.append(f"Ressource: {fuel_delta:+d} carburant.")

    return {
        **progress,
        "coins": max(0, coins),
        "fuel": min(FUEL_CAPACITY_LITERS, max(0, fuel)),
        "repairs_needed": max(0, repairs_needed),
    }, messages


def move(conn, user_id, to_node_id):
    progress = serialize_progression(get_progression(conn, user_id))
    current_node_id = progress["current_node_id"]
    target = get_node(conn, to_node_id)
    if not target:
        raise ApiError(404, "Case introuvable.")
    road = get_road_between(conn, current_node_id, to_node_id)
    if not road:
        raise ApiError(400, "Cette case n'est pas reliee a votre position actuelle.")
    if progress["repairs_needed"] and target["node_type"] != "garage":
        raise ApiError(400, "Panne active: rejoignez un garage avant de continuer.")

    weather_cost = WEATHER_FUEL_COST.get(target["weather"], 0)
    total_fuel_cost = road["fuel_cost"] + weather_cost
    if progress["fuel"] < total_fuel_cost:
        raise ApiError(400, "Pas assez de carburant pour ce trajet.")

    visited = list(progress["visited_nodes"])
    if to_node_id not in visited:
        visited.append(to_node_id)

    progress.update(
        {
            "current_node_id": to_node_id,
            "visited_nodes": visited,
            "distance_km": progress["distance_km"] + road["distance_km"],
            "fuel": progress["fuel"] - total_fuel_cost,
            "coins": 0,
        }
    )
    progress, node_messages = _apply_node_resource(progress, target)
    progress_row = update_progression(conn, user_id, **{key: value for key, value in progress.items() if key != "user_id"})

    event_payload = None
    event = _random_event(conn, road)
    if event:
        import json

        effect = json.loads(event["effect_json"])
        after_event = serialize_progression(progress_row)
        after_event.update(
            {
                "xp": after_event["xp"] + int(effect.get("xp", 0)),
                "fuel": after_event["fuel"] + int(effect.get("fuel", 0)),
                "coins": after_event["coins"] + int(effect.get("coins", 0)),
                "repairs_needed": after_event["repairs_needed"] + int(effect.get("repairs_needed", 0)),
                "successful_events": after_event["successful_events"] + int(effect.get("successful_events", 0)),
            }
        )
        progress_row = update_progression(conn, user_id, **{key: value for key, value in after_event.items() if key != "user_id"})
        event_payload = {
            "slug": event["slug"],
            "name": event["name"],
            "type": event["event_type"],
            "description": event["description"],
            "effect": effect,
        }

    progress_row = sync_unlocks_and_achievements(conn, user_id, progress_row)
    return {
        "move": {
            "from": current_node_id,
            "to": to_node_id,
            "road": road,
            "weather": target["weather"],
            "weather_fuel_cost": weather_cost,
            "messages": node_messages,
        },
        "event": event_payload,
        "progression": serialize_progression(progress_row),
    }
