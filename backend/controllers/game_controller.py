from backend.controllers.auth_controller import require_user
from backend.services.card_service import apply_special_card, complete_trajet_card, discard_trajet_card, draw_cards, get_catalog, get_history, get_user_inventory
from backend.services.game_service import move
from backend.services.map_service import get_map
from backend.services.progression_service import get_progression, serialize_progression
from backend.services.session_service import accept_carpooler, activate_task, apply_session_special_card, choose_starting_trajets, complete_session_trajet, complete_task, create_session, discard_session_trajet, draw_turn_cards, draw_turn_trajets, finish_turn, get_session_or_error, join_session, leave_session, list_sessions, move_in_session, player_interaction, roll_die, selectable_spawns, select_spawn, serialize_session, start_session, use_city_service
from backend.services.skin_service import equip_skin, fuse_skin, list_skins, lootbox_count, open_lootbox


def map_payload(request):
    return get_map(request.conn)


def catalog(request):
    return get_catalog(request.conn)


def progression(request):
    user = require_user(request)
    return serialize_progression(get_progression(request.conn, user["id"]))


def inventory(request):
    user = require_user(request)
    return {"inventory": get_user_inventory(request.conn, user["id"])}


def draw(request):
    user = require_user(request)
    count = int(request.json.get("count", 3))
    if request.json.get("session_code"):
        return draw_turn_cards(request.conn, user["id"], request.json.get("session_code"), count=max(1, min(5, count)))
    return draw_cards(request.conn, user["id"], count=max(1, min(5, count)))


def complete_card(request):
    user = require_user(request)
    if request.json.get("session_code"):
        return complete_session_trajet(request.conn, user["id"], request.json.get("session_code"), int(request.json.get("inventory_id", 0)))
    return complete_trajet_card(request.conn, user["id"], int(request.json.get("inventory_id", 0)))


def apply_card(request):
    user = require_user(request)
    if request.json.get("session_code"):
        return apply_session_special_card(request.conn, user["id"], request.json.get("session_code"), int(request.json.get("inventory_id", 0)))
    return apply_special_card(request.conn, user["id"], int(request.json.get("inventory_id", 0)))


def move_to_node(request):
    user = require_user(request)
    if request.json.get("session_code"):
        return move_in_session(request.conn, user["id"], request.json.get("session_code"), request.json.get("to_node_id"), request.json.get("route_id"))
    return move(request.conn, user["id"], request.json.get("to_node_id"))


def skins(request):
    user = require_user(request)
    return {"skins": list_skins(request.conn, user["id"]), "lootboxes": lootbox_count(request.conn, user["id"])}


def equip(request):
    user = require_user(request)
    return equip_skin(request.conn, user["id"], request.json.get("slug"))


def open_skin_lootbox(request):
    user = require_user(request)
    return open_lootbox(request.conn, user["id"])


def fuse_skin_copies(request):
    user = require_user(request)
    return fuse_skin(request.conn, user["id"], request.json.get("slug"))


def history(request):
    user = require_user(request)
    return {"history": get_history(request.conn, user["id"])}


def sessions(request):
    user = require_user(request)
    return {"sessions": list_sessions(request.conn, user["id"])}


def create_game_session(request):
    user = require_user(request)
    return create_session(
        request.conn,
        user["id"],
        request.json.get("name"),
        request.json.get("max_players", 6),
        request.json.get("visibility", "private"),
        request.json.get("game_mode", "classic"),
    )


def join_game_session(request):
    user = require_user(request)
    return join_session(request.conn, user["id"], request.json.get("code"))


def get_game_session(request):
    user = require_user(request)
    session = get_session_or_error(request.conn, user["id"], request.json.get("code"))
    return serialize_session(request.conn, session, user["id"])


def end_turn(request):
    user = require_user(request)
    return finish_turn(request.conn, user["id"], request.json.get("session_code"), "pass", "Tour passe.")


def roll_session_die(request):
    user = require_user(request)
    return roll_die(request.conn, user["id"], request.json.get("session_code"))


def complete_city_task(request):
    user = require_user(request)
    return complete_task(request.conn, user["id"], request.json.get("session_code"), request.json.get("difficulty"))


def activate_city_task(request):
    user = require_user(request)
    return activate_task(request.conn, user["id"], request.json.get("session_code"), request.json.get("difficulty"))


def spawns(request):
    require_user(request)
    return {"spawns": selectable_spawns(request.conn)}


def select_game_spawn(request):
    user = require_user(request)
    return select_spawn(request.conn, user["id"], request.json.get("session_code"), request.json.get("node_id"))


def start_game_session(request):
    user = require_user(request)
    return start_session(request.conn, user["id"], request.json.get("session_code"))


def choose_game_starting_trajets(request):
    user = require_user(request)
    return choose_starting_trajets(
        request.conn,
        user["id"],
        request.json.get("session_code"),
        request.json.get("inventory_ids") or [],
    )


def leave_game_session(request):
    user = require_user(request)
    return leave_session(request.conn, user["id"], request.json.get("session_code"))


def draw_trajets(request):
    user = require_user(request)
    return draw_turn_trajets(request.conn, user["id"], request.json.get("session_code"))


def discard_card(request):
    user = require_user(request)
    if request.json.get("session_code"):
        return discard_session_trajet(request.conn, user["id"], request.json.get("session_code"), int(request.json.get("inventory_id", 0)))
    return discard_trajet_card(request.conn, user["id"], int(request.json.get("inventory_id", 0)))


def accept_session_carpooler(request):
    user = require_user(request)
    return accept_carpooler(request.conn, user["id"], request.json.get("session_code"), int(request.json.get("carpooler_id", 0)))


def use_service(request):
    user = require_user(request)
    return use_city_service(request.conn, user["id"], request.json.get("session_code"), request.json.get("service_type"))


def interact_with_player(request):
    user = require_user(request)
    return player_interaction(
        request.conn,
        user["id"],
        request.json.get("session_code"),
        request.json.get("target_user_id"),
        request.json.get("interaction_type"),
    )
