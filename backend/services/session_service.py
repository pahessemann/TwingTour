import json
import math
import random
import secrets

from backend.models.errors import ApiError
from backend.services.card_service import choose_initial_trajets, draw_session_trajet_cards, draw_special_cards, get_starting_trajet_choices, get_user_inventory, setup_initial_trajet_choices
from backend.services.map_service import get_board_route, get_board_routes_between, get_node, get_road_between, route_position
from backend.services.progression_service import get_progression, serialize_progression, sync_unlocks_and_achievements, update_progression
from backend.services.seed_service import CAPITAL_NODE_IDS


FEATURE_WEIGHTS = [
    ("card", 22),
    ("station", 14),
    ("garage", 11),
    ("peage", 10),
    ("bonus", 9),
    ("weather", 4),
]

ROAD_DURABILITY_COST = {"autoroute": 3, "nationale": 7, "departementale": 13}
VICTORY_TARGET = 150
TOUR_EUROPE_COUNTRY_TARGET = 12
PUBLIC_CONTRACT_CHANCE = 0.16
FUEL_CAPACITY_LITERS = 35
STARTING_SESSION_COINS = 140
MAX_DURABILITY = 100
LOW_DURABILITY_THRESHOLD = 30
CARPOOLER_NAMES = ["Mila", "Nora", "Elias", "Samir", "Greta", "Lina", "Oskar", "Lea"]
CONTRACT_TITLES = [
    "Course municipale express",
    "Twingo parade improvisee",
    "Colis prioritaire du maire",
    "Rendez-vous du Twingo Club",
    "Livraison de croissants transfrontaliere",
]

WEATHER_FUEL_COST = {
    "clear": 0,
    "rain": 2,
    "fog": 3,
    "snow": 5,
    "wind": 2,
    "heat": 2,
}


def _loads(value, fallback):
    try:
        return json.loads(value or fallback)
    except json.JSONDecodeError:
        return json.loads(fallback)


def _generate_code(conn):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(60):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not conn.execute("SELECT 1 FROM game_sessions WHERE code = ?", (code,)).fetchone():
            return code
    raise ApiError(500, "Impossible de generer un code de partie.")


def _weighted_feature(rng, node):
    if node["id"] in CAPITAL_NODE_IDS:
        return "tasks"
    if node["node_type"] in ("station", "garage"):
        if rng.random() < 0.58:
            return node["node_type"]
    total = sum(weight for _, weight in FEATURE_WEIGHTS)
    pick = rng.randint(1, total)
    cursor = 0
    for feature, weight in FEATURE_WEIGHTS:
        cursor += weight
        if pick <= cursor:
            return feature
    return "tasks"


def _feature_payload(feature, rng):
    if feature == "tasks":
        return {"fuel_price": rng.randint(34, 44), "repair_price": rng.randint(20, 34), "capital_services": True}
    if feature == "station":
        return {"fuel_price": rng.randint(34, 44), "fuel_to": FUEL_CAPACITY_LITERS}
    if feature == "garage":
        return {"repair_price": rng.randint(20, 34), "bonus_fuel": rng.randint(6, 12)}
    if feature == "peage":
        return {"extra_cost": rng.randint(4, 14)}
    if feature == "bonus":
        return {"coins": rng.randint(10, 24), "fuel": rng.randint(0, 6), "durability": rng.randint(0, 8)}
    if feature == "card":
        return {}
    if feature == "weather":
        return {"fuel_penalty": rng.randint(2, 7)}
    return {}


def _nearest_node_id(node, candidates):
    choices = [candidate for candidate in candidates if candidate["id"] != node["id"]]
    if not choices:
        return None
    choices.sort(key=lambda item: (item["x"] - node["x"]) ** 2 + (item["y"] - node["y"]) ** 2)
    return choices[0]["id"]


def _generate_tasks(node, rng, neighbor_ids=None, all_nodes=None):
    city = node["city"]
    country = node["country"]
    all_nodes = all_nodes or []
    if node["id"] in CAPITAL_NODE_IDS:
        nearest_capital = _nearest_node_id(node, [item for item in all_nodes if item["id"] in CAPITAL_NODE_IDS])
        random_city = rng.choice([item for item in all_nodes if item["id"] != node["id"]])["id"] if len(all_nodes) > 1 else nearest_capital
        return [
            {
                "mission_type": "immobilisation",
                "difficulty": "courses",
                "speed": "local",
                "title": f"Courses de quartier a {city}",
                "description": "Rester en ville pour rendre service au quartier.",
                "reward_coins": 50,
                "reward_xp": 0,
                "reward_durability": 0,
                "victory_points": 0,
                "duration_turns": 2,
                "fuel_cost": 0,
                "risk": 0,
                "completed_by": None,
            },
            {
                "mission_type": "teleport_capital",
                "difficulty": "capitale",
                "speed": "express",
                "title": "Covoitureur vers la capitale la plus proche",
                "description": "Au tour suivant, le passager vous emmene dans la capitale la plus proche.",
                "target_node_id": nearest_capital,
                "reward_coins": 0,
                "reward_xp": 0,
                "reward_durability": 0,
                "victory_points": 0,
                "duration_turns": 1,
                "fuel_cost": 0,
                "risk": 0,
                "completed_by": None,
            },
            {
                "mission_type": "teleport_random",
                "difficulty": "mystere",
                "speed": "inconnu",
                "title": "Covoitureur mystere",
                "description": "Au tour suivant, la Twingo arrive dans une ville aleatoire de la carte.",
                "target_node_id": random_city,
                "reward_coins": 70,
                "reward_xp": 0,
                "reward_durability": 0,
                "victory_points": 0,
                "duration_turns": 1,
                "fuel_cost": 0,
                "risk": 0,
                "completed_by": None,
            },
        ]

    if neighbor_ids and rng.randint(0, 1) == 0:
        target_node_id = rng.choice(sorted(neighbor_ids))
        return [
            {
                "mission_type": "deplacement",
                "difficulty": "livraison",
                "speed": "route",
                "title": f"Livraison depuis {city}",
                "description": "Livrer un colis dans la ville voisine indiquee.",
                "target_node_id": target_node_id,
                "reward_coins": rng.randint(24, 44),
                "reward_xp": 0,
                "reward_durability": 0,
                "victory_points": 0,
                "duration_turns": 1,
                "fuel_cost": 0,
                "risk": 0,
                "completed_by": None,
            }
        ]

    if rng.randint(0, 1) == 0:
        return [
            {
                "mission_type": "meteo_block",
                "difficulty": "meteo",
                "speed": "attente",
                "title": f"Intemperies a {city}",
                "description": "La meteo bloque le depart, mieux vaut attendre.",
                "reward_coins": 0,
                "reward_xp": 0,
                "reward_durability": 0,
                "victory_points": 0,
                "duration_turns": 2,
                "fuel_cost": 0,
                "risk": 0,
                "completed_by": None,
            }
        ]
    return [
        {
            "mission_type": "meteo_double",
            "difficulty": "double-de",
            "speed": "fenetre meteo",
            "title": f"Eclaircie favorable a {city}",
            "description": "La route se degage: gagnez immediatement un double de.",
            "reward_coins": 0,
            "reward_xp": 0,
            "reward_durability": 0,
            "victory_points": 0,
            "duration_turns": 1,
            "fuel_cost": 0,
            "risk": 0,
            "double_die": True,
            "completed_by": None,
        }
    ]


def _seed_city_states(conn, session_id, code):
    nodes = [dict(row) for row in conn.execute("SELECT * FROM map_nodes ORDER BY id").fetchall()]
    neighbor_map = {node["id"]: set() for node in nodes}
    for road in conn.execute("SELECT from_node_id, to_node_id FROM roads").fetchall():
        neighbor_map.setdefault(road["from_node_id"], set()).add(road["to_node_id"])
        neighbor_map.setdefault(road["to_node_id"], set()).add(road["from_node_id"])
    rows = []
    for node in nodes:
        rng = random.Random(f"{code}:{node['id']}")
        feature = _weighted_feature(rng, node)
        rows.append(
            (
                session_id,
                node["id"],
                feature,
                json.dumps(_feature_payload(feature, rng)),
                json.dumps(_generate_tasks(node, rng, neighbor_map.get(node["id"]), nodes)),
            )
        )
    conn.executemany(
        """
        INSERT INTO session_city_states (session_id, node_id, feature_type, feature_payload_json, tasks_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _serialize_player(row):
    data = dict(row)
    data["visited_nodes"] = _loads(data.pop("visited_nodes_json"), "[]")
    data["board_position"] = _loads(data.pop("board_position_json"), '{"kind":"city","node_id":"PAR"}')
    data["visited_board_cases"] = _loads(data.pop("visited_board_cases_json"), "[]")
    data["current_node_id"] = data["position_node_id"]
    return data


def _serialize_city_state(row):
    data = dict(row)
    data["feature_payload"] = _loads(data.pop("feature_payload_json"), "{}")
    data["tasks"] = _loads(data.pop("tasks_json"), "[]")
    return data


def _is_user(value, user_id):
    return str(value) == str(user_id)


def _mission_payload(task, row, status):
    return {
        **task,
        "origin_node_id": row["node_id"],
        "city": row["city"],
        "country": row["country"],
        "status": status,
    }


def _session_missions(conn, session_id, user_id):
    missions = {"active": [], "completed": []}
    rows = conn.execute(
        """
        SELECT session_city_states.*, map_nodes.city, map_nodes.country
        FROM session_city_states
        JOIN map_nodes ON map_nodes.id = session_city_states.node_id
        WHERE session_city_states.session_id = ?
        ORDER BY map_nodes.country, map_nodes.city
        """,
        (session_id,),
    ).fetchall()
    for row in rows:
        city_state = _serialize_city_state(row)
        for task in city_state["tasks"]:
            if _is_user(task.get("active_by"), user_id):
                missions["active"].append(_mission_payload(task, row, "active"))
            if _is_user(task.get("completed_by"), user_id):
                missions["completed"].append(_mission_payload(task, row, "completed"))
    return missions


def _visited_country_count(conn, visited_nodes):
    if not visited_nodes:
        return 0
    placeholders = ",".join("?" for _ in visited_nodes)
    row = conn.execute(
        f"SELECT COUNT(DISTINCT country) AS count FROM map_nodes WHERE id IN ({placeholders})",
        visited_nodes,
    ).fetchone()
    return int(row["count"] if row else 0)


def _session_contracts(conn, session_id):
    rows = conn.execute(
        """
        SELECT session_contracts.*, map_nodes.city AS target_city, map_nodes.country AS target_country,
               users.display_name AS claimed_by_name
        FROM session_contracts
        JOIN map_nodes ON map_nodes.id = session_contracts.target_node_id
        LEFT JOIN users ON users.id = session_contracts.claimed_by_user_id
        WHERE session_contracts.session_id = ?
          AND session_contracts.status IN ('active', 'claimed')
        ORDER BY
          CASE session_contracts.status WHEN 'active' THEN 0 ELSE 1 END,
          session_contracts.id DESC
        LIMIT 6
        """,
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _session_row(conn, code):
    return conn.execute("SELECT * FROM game_sessions WHERE code = ?", ((code or "").strip().upper(),)).fetchone()


def _membership(conn, session_id, user_id):
    return conn.execute(
        """
        SELECT session_players.*, users.display_name, users.email
        FROM session_players
        JOIN users ON users.id = session_players.user_id
        WHERE session_players.session_id = ? AND session_players.user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()


def get_session_or_error(conn, user_id, code):
    session = _session_row(conn, code)
    if not session:
        raise ApiError(404, "Partie introuvable.")
    if not _membership(conn, session["id"], user_id):
        raise ApiError(403, "Vous n'etes pas dans cette partie.")
    return session


def serialize_session(conn, session, user_id):
    players = [
        _serialize_player(row)
        for row in conn.execute(
            """
            SELECT session_players.*, users.display_name, users.email,
                   progression.equipped_skin_slug
            FROM session_players
            JOIN users ON users.id = session_players.user_id
            LEFT JOIN progression ON progression.user_id = users.id
            WHERE session_players.session_id = ?
            ORDER BY session_players.joined_at, session_players.user_id
            """,
            (session["id"],),
        ).fetchall()
    ]
    for player in players:
        player["visited_countries_count"] = _visited_country_count(conn, player["visited_nodes"])
    city_states = {
        row["node_id"]: _serialize_city_state(row)
        for row in conn.execute("SELECT * FROM session_city_states WHERE session_id = ?", (session["id"],)).fetchall()
    }
    logs = [
        dict(row)
        for row in conn.execute(
            """
            SELECT session_turn_logs.*, users.display_name
            FROM session_turn_logs
            JOIN users ON users.id = session_turn_logs.user_id
            WHERE session_turn_logs.session_id = ?
            ORDER BY session_turn_logs.id DESC
            LIMIT 8
            """,
            (session["id"],),
        ).fetchall()
    ]
    carpoolers = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM session_carpoolers WHERE session_id = ? ORDER BY id",
            (session["id"],),
        ).fetchall()
    ]
    me = next((player for player in players if player["user_id"] == user_id), None)
    current_player = next((player for player in players if player["user_id"] == session["current_turn_user_id"]), None)
    me_is_in_city = me and me.get("board_position", {}).get("kind") == "city"
    starting_choices = get_starting_trajet_choices(conn, user_id, session["id"]) if session["status"] in ("active", "closing") else []
    return {
        **dict(session),
        "final_standings": _loads(session["final_standings_json"], "[]") if "final_standings_json" in session.keys() else [],
        "players": players,
        "me": me,
        "is_member": bool(me),
        "current_player": current_player,
        "is_my_turn": session["current_turn_user_id"] == user_id,
        "city_states": city_states,
        "current_city_state": city_states.get(me["current_node_id"]) if me_is_in_city else None,
        "turn_logs": logs,
        "carpoolers": carpoolers,
        "missions": _session_missions(conn, session["id"], user_id),
        "leaderboard": _session_leaderboard(conn, players),
        "contracts": _session_contracts(conn, session["id"]),
        "capital_node_ids": sorted(CAPITAL_NODE_IDS),
        "tour_country_target": TOUR_EUROPE_COUNTRY_TARGET,
        "starting_trajet_choices": starting_choices,
        "needs_starting_trajet_choice": bool(starting_choices),
    }


def _session_leaderboard(conn, players):
    rows = []
    for player in players:
        active_malus = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM inventory
            JOIN cards ON cards.id = inventory.item_id
            WHERE inventory.user_id = ?
              AND inventory.status = 'active'
              AND inventory.session_id = ?
              AND cards.type = 'malus'
            """,
            (player["user_id"], player["session_id"]),
        ).fetchone()["count"]
        score = (
            int(player["victory_points"])
            + int(player["completed_trajets"]) * 4
            + max(0, int(player["coins"]) - STARTING_SESSION_COINS) // 25
            + max(0, int(player["fuel"]) - FUEL_CAPACITY_LITERS) // 5
            + max(0, int(player["durability"]) - MAX_DURABILITY) // 10
            - int(player["repairs_needed"]) * 5
            - active_malus * 3
        )
        rows.append({"user_id": player["user_id"], "display_name": player["display_name"], "score": max(0, score)})
    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def _session_visibility(value):
    return "public" if str(value or "").strip().lower() == "public" else "private"


def _session_game_mode(value):
    return "tour_europe" if str(value or "").strip().lower() in ("tour_europe", "tour", "europe") else "classic"


def create_session(conn, user_id, name=None, max_players=6, visibility="private", game_mode="classic"):
    code = _generate_code(conn)
    session_name = (name or f"Partie {code}").strip()[:48]
    session_visibility = _session_visibility(visibility)
    session_mode = _session_game_mode(game_mode)
    cursor = conn.execute(
        """
        INSERT INTO game_sessions (code, name, visibility, game_mode, status, created_by_user_id, current_turn_user_id, max_players)
        VALUES (?, ?, ?, ?, 'lobby', ?, ?, ?)
        """,
        (code, session_name, session_visibility, session_mode, user_id, user_id, max(2, min(8, int(max_players or 6)))),
    )
    session_id = cursor.lastrowid
    conn.execute(
        """
        INSERT INTO session_players (session_id, user_id, position_node_id, spawn_node_id, fuel, coins, visited_nodes_json, is_ready)
        VALUES (?, ?, 'PAR', 'PAR', ?, 140, '["PAR"]', 1)
        """,
        (session_id, user_id, FUEL_CAPACITY_LITERS),
    )
    _seed_city_states(conn, session_id, code)
    return serialize_session(conn, _session_row(conn, code), user_id)


def join_session(conn, user_id, code):
    clean_code = (code or "").strip().upper()
    session = _session_row(conn, clean_code)
    if not session:
        raise ApiError(404, "Code de partie invalide.")
    if session["status"] not in ("lobby", "active"):
        raise ApiError(400, "Cette partie n'est plus ouverte.")
    if _membership(conn, session["id"], user_id):
        return serialize_session(conn, session, user_id)
    player_count = conn.execute("SELECT COUNT(*) AS count FROM session_players WHERE session_id = ?", (session["id"],)).fetchone()["count"]
    if player_count >= session["max_players"]:
        raise ApiError(400, "Cette partie est complete.")
    conn.execute(
        """
        INSERT INTO session_players (session_id, user_id, position_node_id, spawn_node_id, fuel, coins, visited_nodes_json)
        VALUES (?, ?, 'PAR', 'PAR', ?, 140, '["PAR"]')
        """,
        (session["id"], user_id, FUEL_CAPACITY_LITERS),
    )
    return serialize_session(conn, session, user_id)


def list_sessions(conn, user_id):
    rows = conn.execute(
        """
        SELECT DISTINCT game_sessions.*,
               CASE WHEN member.user_id IS NULL THEN 0 ELSE 1 END AS is_member_sort
        FROM game_sessions
        LEFT JOIN session_players AS member
          ON member.session_id = game_sessions.id
         AND member.user_id = ?
        WHERE (
              member.user_id IS NOT NULL
              AND game_sessions.status IN ('lobby', 'active', 'closing', 'finished')
            )
           OR (
              game_sessions.visibility = 'public'
              AND game_sessions.status = 'lobby'
            )
        ORDER BY is_member_sort DESC, game_sessions.updated_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [serialize_session(conn, row, user_id) for row in rows]


def selectable_spawns(conn):
    rows = conn.execute("SELECT * FROM map_nodes ORDER BY country, city").fetchall()
    return [dict(row) for row in rows if row["id"] in CAPITAL_NODE_IDS]


def select_spawn(conn, user_id, code, node_id):
    session = get_session_or_error(conn, user_id, code)
    if session["status"] != "lobby":
        raise ApiError(400, "Le spawn ne peut etre choisi qu'avant le lancement.")
    if node_id not in CAPITAL_NODE_IDS:
        raise ApiError(400, "Choisissez une capitale comme ville de depart.")
    if not get_node(conn, node_id):
        raise ApiError(404, "Ville de depart introuvable.")
    visited = json.dumps([node_id])
    conn.execute(
        """
        UPDATE session_players
        SET spawn_node_id = ?, position_node_id = ?, board_position_json = ?, visited_nodes_json = ?, is_ready = 1
        WHERE session_id = ? AND user_id = ?
        """,
        (node_id, node_id, json.dumps({"kind": "city", "node_id": node_id}), visited, session["id"], user_id),
    )
    return serialize_session(conn, session, user_id)


def _prepare_initial_trajet_choices(conn, session_id, user_id, spawn_node_id):
    conn.execute(
        """
        UPDATE inventory
        SET status = 'archived'
        WHERE user_id = ? AND item_type = 'card' AND status IN ('active', 'choice')
        """,
        (user_id,),
    )
    setup_initial_trajet_choices(conn, user_id, session_id, spawn_node_id)


def _seed_carpoolers(conn, session_id):
    if conn.execute("SELECT COUNT(*) AS count FROM session_carpoolers WHERE session_id = ?", (session_id,)).fetchone()["count"]:
        return
    player_spawns = {
        row["spawn_node_id"]
        for row in conn.execute("SELECT spawn_node_id FROM session_players WHERE session_id = ?", (session_id,)).fetchall()
    }
    nodes = [dict(row) for row in conn.execute("SELECT * FROM map_nodes").fetchall()]
    candidates = [node for node in nodes if node["id"] not in player_spawns]
    rows = []
    for index in range(4):
        start = random.choice(candidates)
        destinations = [node for node in nodes if node["country"] != start["country"] and node["id"] != start["id"]]
        destination = random.choice(destinations)
        rows.append(
            (
                session_id,
                CARPOOLER_NAMES[index % len(CARPOOLER_NAMES)],
                start["id"],
                destination["id"],
                random.randint(18, 38),
                random.randint(18, 55),
                random.randint(0, 12),
                random.randint(2, 5),
            )
        )
    conn.executemany(
        """
        INSERT INTO session_carpoolers (session_id, name, start_node_id, destination_node_id, victory_points, reward_coins, reward_durability, min_turns)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def start_session(conn, user_id, code):
    session = get_session_or_error(conn, user_id, code)
    if session["created_by_user_id"] != user_id:
        raise ApiError(403, "Seul l'hote peut lancer la partie.")
    if session["status"] != "lobby":
        raise ApiError(400, "Cette partie est deja lancee ou terminee.")
    players = conn.execute("SELECT * FROM session_players WHERE session_id = ? ORDER BY joined_at, user_id", (session["id"],)).fetchall()
    if not players:
        raise ApiError(400, "Aucun joueur dans la partie.")
    for player in players:
        _prepare_initial_trajet_choices(conn, session["id"], player["user_id"], player["spawn_node_id"])
        conn.execute(
            """
            UPDATE session_players
            SET position_node_id = spawn_node_id, board_position_json = ?, visited_board_cases_json = '[]',
                visited_nodes_json = ?, fuel = ?,
                coins = ?, durability = ?, repairs_needed = 0, distance_km = 0,
                completed_trajets = 0, xp = 0, victory_points = 0,
                mission_locked_turns = 0, dice_remaining = 0, turn_roll = 0,
                trajet_draws_long = 0, trajet_draws_short = 0
            WHERE session_id = ? AND user_id = ?
            """,
            (
                json.dumps({"kind": "city", "node_id": player["spawn_node_id"]}),
                json.dumps([player["spawn_node_id"]]),
                FUEL_CAPACITY_LITERS,
                STARTING_SESSION_COINS,
                MAX_DURABILITY,
                session["id"],
                player["user_id"],
            ),
        )
    _seed_carpoolers(conn, session["id"])
    conn.execute(
        """
        UPDATE game_sessions
        SET status = 'active', current_turn_user_id = ?, turn_number = 1, round_number = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (players[0]["user_id"], session["id"]),
    )
    return serialize_session(conn, _session_row(conn, session["code"]), user_id)


def leave_session(conn, user_id, code):
    session = get_session_or_error(conn, user_id, code)
    conn.execute(
        """
        UPDATE inventory
        SET status = 'archived'
        WHERE user_id = ? AND item_type = 'card' AND status IN ('active', 'choice') AND (session_id = ? OR session_id IS NULL)
        """,
        (user_id, session["id"]),
    )
    conn.execute("DELETE FROM session_players WHERE session_id = ? AND user_id = ?", (session["id"], user_id))
    remaining = conn.execute("SELECT user_id FROM session_players WHERE session_id = ? ORDER BY joined_at, user_id", (session["id"],)).fetchall()
    if not remaining:
        conn.execute("DELETE FROM game_sessions WHERE id = ?", (session["id"],))
        return {"left": True, "sessions": []}
    next_host = remaining[0]["user_id"]
    current_turn = session["current_turn_user_id"] if any(row["user_id"] == session["current_turn_user_id"] for row in remaining) else next_host
    conn.execute(
        """
        UPDATE game_sessions
        SET created_by_user_id = CASE WHEN created_by_user_id = ? THEN ? ELSE created_by_user_id END,
            current_turn_user_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (user_id, next_host, current_turn, session["id"]),
    )
    return {"left": True, "sessions": list_sessions(conn, user_id)}


def _require_turn(session, user_id):
    if session["status"] not in ("active", "closing"):
        raise ApiError(409, "La partie n'est pas lancee.")
    if session["current_turn_user_id"] != user_id:
        raise ApiError(409, "Ce n'est pas votre tour.")


def _require_playable_turn(conn, session, user_id):
    _require_turn(session, user_id)
    if get_starting_trajet_choices(conn, user_id, session["id"]):
        raise ApiError(409, "Choisissez vos 3 trajets de depart avant de jouer.")
    player = _membership(conn, session["id"], user_id)
    if player and player["mission_locked_turns"] > 0:
        raise ApiError(409, "Mission en cours: passez ce tour pour terminer l'attente.")


def _finalize_session(conn, session):
    rows = conn.execute(
        """
        SELECT session_players.*, users.display_name
        FROM session_players
        JOIN users ON users.id = session_players.user_id
        WHERE session_players.session_id = ?
        """,
        (session["id"],),
    ).fetchall()
    standings = []
    for row in rows:
        active_malus = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM inventory
            JOIN cards ON cards.id = inventory.item_id
            WHERE inventory.user_id = ?
              AND inventory.status = 'active'
              AND inventory.session_id = ?
              AND cards.type = 'malus'
            """,
            (row["user_id"], session["id"]),
        ).fetchone()["count"]
        penalty = int(row["repairs_needed"]) * 5 + active_malus * 3 + max(0, 40 - int(row["durability"])) // 5
        management_bonus = (
            max(0, int(row["fuel"]) - FUEL_CAPACITY_LITERS) // 5
            + max(0, int(row["durability"]) - MAX_DURABILITY) // 10
            + max(0, int(row["coins"]) - STARTING_SESSION_COINS) // 25
        )
        base_score = int(row["victory_points"]) + int(row["completed_trajets"]) * 4 + management_bonus
        standings.append(
            {
                "user_id": row["user_id"],
                "display_name": row["display_name"],
                "victory_points": row["victory_points"],
                "penalty": penalty,
                "final_score": max(0, base_score - penalty),
            }
        )
    standings.sort(key=lambda item: item["final_score"], reverse=True)
    winner_id = standings[0]["user_id"] if standings else session["winner_user_id"]
    conn.execute(
        """
        UPDATE game_sessions
        SET status = 'finished', winner_user_id = ?, final_standings_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (winner_id, json.dumps(standings), session["id"]),
    )


def _advance_turn(conn, session):
    players = [
        row["user_id"]
        for row in conn.execute(
            "SELECT user_id FROM session_players WHERE session_id = ? ORDER BY joined_at, user_id",
            (session["id"],),
        ).fetchall()
    ]
    if not players:
        return
    try:
        index = players.index(session["current_turn_user_id"])
    except ValueError:
        index = -1
    wrapped = index >= len(players) - 1
    if session["status"] == "closing" and wrapped:
        _finalize_session(conn, session)
        return
    next_user = players[(index + 1) % len(players)]
    next_round = session["round_number"] + 1 if wrapped else session["round_number"]
    conn.execute(
        """
        UPDATE game_sessions
        SET current_turn_user_id = ?, turn_number = turn_number + 1, round_number = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (next_user, next_round, session["id"]),
    )
    conn.execute(
        """
        UPDATE session_players
        SET dice_remaining = 0, turn_roll = 0, trajet_draws_long = 0, trajet_draws_short = 0
        WHERE session_id = ? AND user_id = ?
        """,
        (session["id"], next_user),
    )
    if wrapped:
        updated_session = {**dict(session), "round_number": next_round}
        _expire_contracts(conn, updated_session)
        _maybe_spawn_public_contract(conn, updated_session)


def finish_turn(conn, user_id, code, action_type="pass", summary="Tour passe."):
    session = get_session_or_error(conn, user_id, code)
    _require_turn(session, user_id)
    if action_type != "initial_trajets" and get_starting_trajet_choices(conn, user_id, session["id"]):
        raise ApiError(409, "Choisissez vos 3 trajets de depart avant de passer le tour.")
    player = _membership(conn, session["id"], user_id)
    if player and player["mission_locked_turns"] > 0 and action_type != "task":
        conn.execute(
            "UPDATE session_players SET mission_locked_turns = mission_locked_turns - 1 WHERE session_id = ? AND user_id = ?",
            (session["id"], user_id),
        )
        summary = "Mission en cours: tour bloque sans consommation."
    special_messages = _tick_active_special_cards(conn, session, user_id)
    if special_messages:
        summary = f"{summary} {' '.join(special_messages)}"
    conn.execute(
        "INSERT INTO session_turn_logs (session_id, user_id, action_type, summary) VALUES (?, ?, ?, ?)",
        (session["id"], user_id, action_type, summary),
    )
    conn.execute(
        "UPDATE session_players SET dice_remaining = 0, turn_roll = 0, last_action_at = CURRENT_TIMESTAMP WHERE session_id = ? AND user_id = ?",
        (session["id"], user_id),
    )
    _advance_turn(conn, session)
    return serialize_session(conn, _session_row(conn, session["code"]), user_id)


def choose_starting_trajets(conn, user_id, code, inventory_ids):
    session = get_session_or_error(conn, user_id, code)
    if session["status"] not in ("active", "closing"):
        raise ApiError(409, "La partie doit etre lancee pour choisir les trajets de depart.")
    result = choose_initial_trajets(conn, user_id, session["id"], inventory_ids or [])
    return {
        **result,
        "session": serialize_session(conn, _session_row(conn, session["code"]), user_id),
    }


def roll_die(conn, user_id, code):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    if player["dice_remaining"] > 0:
        return {"roll": player["turn_roll"], "session": serialize_session(conn, session, user_id)}
    roll = random.randint(1, 6)
    conn.execute(
        """
        UPDATE session_players
        SET dice_remaining = ?, turn_roll = ?, last_action_at = CURRENT_TIMESTAMP
        WHERE session_id = ? AND user_id = ?
        """,
        (roll, roll, session["id"], user_id),
    )
    return {"roll": roll, "session": serialize_session(conn, _session_row(conn, code), user_id)}


def _update_session_player(conn, session_id, user_id, progress):
    existing_row = _membership(conn, session_id, user_id)
    existing = _serialize_player(existing_row) if existing_row else {}
    conn.execute(
        """
        UPDATE session_players
        SET position_node_id = ?, fuel = ?, coins = ?, durability = ?, repairs_needed = ?,
            board_position_json = ?, visited_board_cases_json = ?, visited_nodes_json = ?,
            distance_km = ?, completed_trajets = ?, xp = ?,
            victory_points = ?, dice_remaining = ?, turn_roll = ?,
            mission_locked_turns = ?, trajet_draws_long = ?, trajet_draws_short = ?,
            last_action_at = CURRENT_TIMESTAMP
        WHERE session_id = ? AND user_id = ?
        """,
        (
            progress["current_node_id"],
            max(0, min(FUEL_CAPACITY_LITERS, int(progress["fuel"]))),
            max(0, int(progress["coins"])),
            max(0, min(MAX_DURABILITY, int(progress.get("durability", MAX_DURABILITY)))),
            max(0, int(progress["repairs_needed"])),
            json.dumps(progress.get("board_position", existing.get("board_position", {"kind": "city", "node_id": progress["current_node_id"]}))),
            json.dumps(progress.get("visited_board_cases", existing.get("visited_board_cases", []))),
            json.dumps(progress["visited_nodes"]),
            int(progress["distance_km"]),
            int(progress["completed_trajets"]),
            int(progress["xp"]),
            int(progress.get("victory_points", 0)),
            max(0, int(progress.get("dice_remaining", existing.get("dice_remaining", 0)))),
            max(0, int(progress.get("turn_roll", existing.get("turn_roll", 0)))),
            max(0, int(progress.get("mission_locked_turns", 0))),
            int(progress.get("trajet_draws_long", 0)),
            int(progress.get("trajet_draws_short", 0)),
            session_id,
            user_id,
        ),
    )


def _random_event(conn, road):
    return None


def _nearest_service_city(conn, session_id, from_node_id, service_type="station"):
    origin = get_node(conn, from_node_id)
    if not origin:
        return None
    rows = conn.execute(
        """
        SELECT session_city_states.*, map_nodes.city, map_nodes.country, map_nodes.x, map_nodes.y
        FROM session_city_states
        JOIN map_nodes ON map_nodes.id = session_city_states.node_id
        WHERE session_city_states.session_id = ?
        """,
        (session_id,),
    ).fetchall()
    candidates = []
    for row in rows:
        state = _serialize_city_state(row)
        is_capital_service = row["node_id"] in CAPITAL_NODE_IDS and service_type in ("station", "garage")
        if state["feature_type"] == service_type or is_capital_service:
            distance = (row["x"] - origin["x"]) ** 2 + (row["y"] - origin["y"]) ** 2
            candidates.append((distance, row["node_id"], state))
    candidates.sort(key=lambda item: item[0])
    return candidates[0] if candidates else None


def _maybe_offer_carpooler(conn, session_id, user_id, current_node_id):
    active = conn.execute(
        "SELECT * FROM session_carpoolers WHERE session_id = ? AND assigned_user_id = ? AND status = 'active'",
        (session_id, user_id),
    ).fetchone()
    if active:
        return None
    row = conn.execute(
        """
        SELECT * FROM session_carpoolers
        WHERE session_id = ? AND status = 'waiting' AND start_node_id = ?
        ORDER BY RANDOM()
        LIMIT 1
        """,
        (session_id, current_node_id),
    ).fetchone()
    return dict(row) if row else None


def _deliver_carpooler_if_needed(conn, session_id, user_id, progress):
    row = conn.execute(
        """
        SELECT * FROM session_carpoolers
        WHERE session_id = ? AND assigned_user_id = ? AND status = 'active' AND destination_node_id = ?
        """,
        (session_id, user_id, progress["current_node_id"]),
    ).fetchone()
    if not row:
        return None
    conn.execute("UPDATE session_carpoolers SET status = 'delivered' WHERE id = ?", (row["id"],))
    progress["victory_points"] += row["victory_points"]
    progress["coins"] += row["reward_coins"]
    progress["durability"] = min(MAX_DURABILITY, progress.get("durability", MAX_DURABILITY) + row["reward_durability"])
    return dict(row)


def _maybe_start_closing(conn, session, user_id, progress_or_victory_points):
    if session["status"] != "active":
        return
    if session["game_mode"] == "tour_europe":
        visited_nodes = progress_or_victory_points.get("visited_nodes", []) if isinstance(progress_or_victory_points, dict) else []
        if _visited_country_count(conn, visited_nodes) < TOUR_EUROPE_COUNTRY_TARGET:
            return
    else:
        victory_points = progress_or_victory_points.get("victory_points", 0) if isinstance(progress_or_victory_points, dict) else progress_or_victory_points
        if victory_points < VICTORY_TARGET:
            return
    conn.execute(
        """
        UPDATE game_sessions
        SET status = 'closing', winner_user_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (user_id, session["id"]),
    )


def _expire_contracts(conn, session):
    conn.execute(
        """
        UPDATE session_contracts
        SET status = 'expired'
        WHERE session_id = ? AND status = 'active' AND expires_round < ?
        """,
        (session["id"], int(session["round_number"])),
    )


def _maybe_spawn_public_contract(conn, session):
    if session["status"] != "active":
        return None
    active = conn.execute(
        "SELECT 1 FROM session_contracts WHERE session_id = ? AND status = 'active' LIMIT 1",
        (session["id"],),
    ).fetchone()
    if active:
        return None
    rng = random.Random(f"{session['code']}:{session['round_number']}:public-contract")
    if rng.random() >= PUBLIC_CONTRACT_CHANCE:
        return None
    occupied = {
        row["position_node_id"]
        for row in conn.execute("SELECT position_node_id FROM session_players WHERE session_id = ?", (session["id"],)).fetchall()
    }
    nodes = [dict(row) for row in conn.execute("SELECT * FROM map_nodes ORDER BY id").fetchall() if row["id"] not in occupied]
    if not nodes:
        return None
    target = rng.choice(nodes)
    title = rng.choice(CONTRACT_TITLES)
    reward_coins = rng.randint(35, 75)
    reward_points = rng.randint(6, 14)
    reward_xp = rng.randint(10, 35)
    expires_round = int(session["round_number"]) + rng.randint(2, 3)
    cursor = conn.execute(
        """
        INSERT INTO session_contracts
          (session_id, title, description, target_node_id, reward_coins, reward_victory_points, reward_xp, created_round, expires_round)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["id"],
            title,
            f"Evenement rare: premier joueur a rejoindre {target['city']} avant la manche {expires_round} remporte le contrat.",
            target["id"],
            reward_coins,
            reward_points,
            reward_xp,
            int(session["round_number"]),
            expires_round,
        ),
    )
    return cursor.lastrowid


def _claim_public_contracts(conn, session, user_id, progress):
    rows = conn.execute(
        """
        SELECT * FROM session_contracts
        WHERE session_id = ?
          AND status = 'active'
          AND target_node_id = ?
          AND expires_round >= ?
        ORDER BY id
        """,
        (session["id"], progress["current_node_id"], int(session["round_number"])),
    ).fetchall()
    claimed = []
    for row in rows:
        conn.execute(
            """
            UPDATE session_contracts
            SET status = 'claimed', claimed_by_user_id = ?
            WHERE id = ? AND status = 'active'
            """,
            (user_id, row["id"]),
        )
        progress["coins"] += int(row["reward_coins"])
        progress["victory_points"] += int(row["reward_victory_points"])
        progress["xp"] += int(row["reward_xp"])
        claimed.append(dict(row))
    return claimed


def _active_special_rows(conn, session_id, user_id):
    return conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.quantity, cards.name, cards.type, cards.effect_json
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ?
          AND inventory.session_id = ?
          AND inventory.item_type = 'card'
          AND inventory.status = 'active'
          AND cards.type IN ('bonus', 'malus')
        ORDER BY inventory.id
        """,
        (user_id, session_id),
    ).fetchall()


def _nearest_capital_id(conn, node_id):
    origin = get_node(conn, node_id)
    if not origin:
        return None
    capitals = [get_node(conn, capital_id) for capital_id in CAPITAL_NODE_IDS]
    capitals = [capital for capital in capitals if capital and capital["id"] != node_id]
    if not capitals:
        return node_id if node_id in CAPITAL_NODE_IDS else None
    capitals.sort(key=lambda item: (item["x"] - origin["x"]) ** 2 + (item["y"] - origin["y"]) ** 2)
    return capitals[0]["id"]


def _is_repair_city(conn, session_id, player):
    if player["board_position"].get("kind") != "city":
        return False
    if player["current_node_id"] in CAPITAL_NODE_IDS:
        return True
    row = conn.execute(
        "SELECT * FROM session_city_states WHERE session_id = ? AND node_id = ?",
        (session_id, player["current_node_id"]),
    ).fetchone()
    return bool(row and _serialize_city_state(row)["feature_type"] == "garage")


def _resolve_mechanical_malus(conn, session_id, user_id, kind="any"):
    resolved = []
    for row in _active_special_rows(conn, session_id, user_id):
        effect = json.loads(row["effect_json"] or "{}")
        mechanical = effect.get("mechanical_malus")
        if not mechanical:
            continue
        if kind != "any" and mechanical != kind:
            continue
        conn.execute("UPDATE inventory SET status = 'completed' WHERE id = ?", (row["inventory_id"],))
        resolved.append(row["name"])
    return resolved


def _movement_special_modifiers(conn, session_id, user_id, fuel_cost):
    adjusted = float(fuel_cost)
    messages = []
    for row in _active_special_rows(conn, session_id, user_id):
        effect = json.loads(row["effect_json"] or "{}")
        if effect.get("fuel_multiplier"):
            adjusted *= float(effect["fuel_multiplier"])
            messages.append(f"{row['name']}: consommation x{effect['fuel_multiplier']}.")
        if effect.get("fuel_discount_percent"):
            discount = max(0, min(90, int(effect["fuel_discount_percent"])))
            adjusted *= (100 - discount) / 100
            messages.append(f"{row['name']}: -{discount}% consommation.")
    return max(0, math.ceil(adjusted)), messages


def _tick_active_special_cards(conn, session, user_id):
    player_row = _membership(conn, session["id"], user_id)
    if not player_row:
        return []
    player = _serialize_player(player_row)
    progress = _board_progress_from_player(player)
    messages = []
    changed = False
    for row in _active_special_rows(conn, session["id"], user_id):
        effect = json.loads(row["effect_json"] or "{}")
        if effect.get("durability_loss_percent_per_turn"):
            percent = int(effect["durability_loss_percent_per_turn"])
            loss = max(1, round(MAX_DURABILITY * percent / 100))
            progress["durability"] = max(0, progress["durability"] - loss)
            messages.append(f"{row['name']}: -{loss} durabilite.")
            changed = True
        if effect.get("turns"):
            remaining = max(0, int(row["quantity"]) - 1)
            if remaining <= 0:
                conn.execute("UPDATE inventory SET status = 'completed', quantity = 0 WHERE id = ?", (row["inventory_id"],))
                messages.append(f"{row['name']} se termine.")
            else:
                conn.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (remaining, row["inventory_id"]))
    if changed:
        _update_session_player(conn, session["id"], user_id, progress)
    return messages


def _apply_city_feature(conn, session_id, user_id, progress, city_state):
    feature = city_state["feature_type"]
    payload = dict(city_state["feature_payload"])
    messages = []
    drawn = None

    if feature == "station":
        price = int(payload.get("fuel_price", 18))
        messages.append(f"Station-service disponible: plein manuel pour {price} pieces.")
    elif feature == "garage":
        price = int(payload.get("repair_price", 26))
        messages.append(f"Garage disponible: reparation manuelle pour {price} pieces.")
    elif feature == "peage":
        extra = int(payload.get("extra_cost", 6))
        progress["coins"] = max(0, progress["coins"] - extra)
        messages.append(f"Peage urbain: -{extra} pieces.")
    elif feature == "bonus":
        coins = int(payload.get("coins", 12))
        fuel = int(payload.get("fuel", 0))
        durability = int(payload.get("durability", 0))
        progress["coins"] += coins
        progress["fuel"] = min(FUEL_CAPACITY_LITERS, progress["fuel"] + fuel)
        progress["durability"] = min(MAX_DURABILITY, progress.get("durability", MAX_DURABILITY) + durability)
        messages.append(f"Bonus local: +{coins} pieces, +{fuel} carburant, +{durability} durabilite.")
    elif feature == "weather":
        penalty = int(payload.get("fuel_penalty", 3))
        progress["fuel"] = max(0, progress["fuel"] - penalty)
        messages.append(f"Zone meteo: -{penalty} carburant.")
    elif feature == "card":
        drawn = draw_special_cards(conn, user_id, 1, session_id=session_id)["drawn"]
        messages.append("Ville bonus/malus: une carte a ete ajoutee automatiquement a votre main.")
    else:
        messages.append("Capitale: activez une mission pour gagner des pieces.")

    conn.execute(
        "UPDATE session_city_states SET feature_payload_json = ? WHERE id = ?",
        (json.dumps(payload), city_state["id"]),
    )
    return progress, messages, drawn


def _board_progress_from_player(player):
    return {
        "current_node_id": player["current_node_id"],
        "visited_nodes": list(player["visited_nodes"]),
        "board_position": player["board_position"],
        "visited_board_cases": list(player["visited_board_cases"]),
        "fuel": player["fuel"],
        "coins": player["coins"],
        "durability": player["durability"],
        "repairs_needed": player["repairs_needed"],
        "distance_km": player["distance_km"],
        "completed_trajets": player["completed_trajets"],
        "xp": player["xp"],
        "victory_points": player["victory_points"],
        "dice_remaining": player["dice_remaining"],
        "turn_roll": player["turn_roll"],
        "mission_locked_turns": player["mission_locked_turns"],
        "trajet_draws_long": player["trajet_draws_long"],
        "trajet_draws_short": player["trajet_draws_short"],
    }


def _apply_board_case(progress, board_case):
    messages = []
    if board_case["kind"] == "empty" or board_case["kind"] == "city":
        return messages
    if board_case["id"] in progress["visited_board_cases"]:
        return messages
    progress["visited_board_cases"].append(board_case["id"])
    effect = dict(board_case.get("effect") or {})
    progress["coins"] += int(effect.get("coins", 0))
    progress["fuel"] += int(effect.get("fuel", 0))
    progress["durability"] += int(effect.get("durability", 0))
    progress["xp"] += int(effect.get("xp", 0))
    if board_case["kind"] == "bonus":
        messages.append("Case bonus: ressources ajoutees.")
    elif board_case["kind"] == "malus":
        messages.append("Case malus: la Twingo encaisse le contretemps.")
    elif board_case["kind"] == "event":
        messages.append("Case evenement: petit detour narratif et XP.")
    elif board_case["kind"] == "bifurcation":
        messages.append("Bifurcation: reperez les prochains choix d'itineraire.")
    return messages


def _route_context(conn, player, to_node_id, route_id):
    board_position = player["board_position"]
    if board_position.get("kind") == "route":
        route = get_board_route(conn, board_position["route_id"])
        if not route:
            raise ApiError(404, "Itineraire introuvable.")
        if route_id and route_id != route["id"]:
            raise ApiError(400, "Vous devez rester sur l'itineraire en cours.")
        endpoints = {route["from_node_id"], route["to_node_id"]}
        target_node_id = to_node_id or board_position["target_node_id"]
        if target_node_id not in endpoints:
            raise ApiError(400, "Destination incompatible avec cet itineraire.")
        direction = 1 if target_node_id == route["to_node_id"] else -1
        return route, target_node_id, int(board_position["index"]), direction

    current_node_id = player["current_node_id"]
    if route_id:
        route = get_board_route(conn, route_id)
        if not route:
            raise ApiError(404, "Itineraire introuvable.")
        endpoints = {route["from_node_id"], route["to_node_id"]}
        if current_node_id not in endpoints:
            raise ApiError(400, "Cet itineraire ne part pas de votre position.")
        target_node_id = to_node_id or (route["to_node_id"] if current_node_id == route["from_node_id"] else route["from_node_id"])
        if target_node_id not in endpoints or target_node_id == current_node_id:
            raise ApiError(400, "Destination incompatible avec cet itineraire.")
    else:
        if not to_node_id:
            raise ApiError(400, "Choisissez une ville ou un itineraire.")
        routes = get_board_routes_between(conn, current_node_id, to_node_id)
        if not routes:
            raise ApiError(400, "Cette ville n'est pas reliee a votre position actuelle.")
        route = routes[0]
        target_node_id = to_node_id

    direction = 1 if current_node_id == route["from_node_id"] else -1
    start_index = 0 if direction == 1 else route["case_count"]
    return route, target_node_id, start_index, direction


def move_in_session(conn, user_id, code, to_node_id, route_id=None):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    if player["dice_remaining"] <= 0:
        raise ApiError(400, "Lancez le de avant de vous deplacer.")

    route, target_node_id, current_index, direction = _route_context(conn, player, to_node_id, route_id)
    active_row, _, active_task = _active_task_entry(conn, session["id"], user_id)
    if active_task and active_task.get("mission_type") == "deplacement" and player["board_position"].get("kind") == "city":
        if active_row["node_id"] == player["current_node_id"] and target_node_id != active_task.get("target_node_id"):
            raise ApiError(400, "Mission de deplacement active: rejoignez la ville indiquee.")
    target = get_node(conn, target_node_id)
    if not target:
        raise ApiError(404, "Ville introuvable.")

    remaining_to_city = route["case_count"] - current_index if direction == 1 else current_index
    steps = min(player["dice_remaining"], remaining_to_city)
    if steps <= 0:
        raise ApiError(400, "Vous etes deja au bout de cet itineraire.")
    new_index = current_index + direction * steps
    arrived_city = new_index in (0, route["case_count"])
    reached_node_id = route["to_node_id"] if new_index == route["case_count"] else route["from_node_id"] if new_index == 0 else None
    board_case = route_position(route, new_index)

    per_case = route["per_case"]
    base_fuel_cost = int(per_case["fuel"]) * steps
    durability_cost = int(per_case["durability"]) * steps
    low_durability_penalty = max(0, round(base_fuel_cost * 0.35)) if player["durability"] < LOW_DURABILITY_THRESHOLD else 0
    total_fuel_cost, modifier_messages = _movement_special_modifiers(conn, session["id"], user_id, base_fuel_cost + low_durability_penalty)
    total_coin_cost = int(per_case["coins"]) * steps
    if player["fuel"] < total_fuel_cost:
        nearest = _nearest_service_city(conn, session["id"], player["current_node_id"], "station")
        if not nearest:
            raise ApiError(400, "Pas assez de carburant et aucune station disponible.")
        _, station_id, station_state = nearest
        tow_cost = int(station_state["feature_payload"].get("fuel_price", 18)) * 2
        visited = list(player["visited_nodes"])
        if station_id not in visited:
            visited.append(station_id)
        progress = {
            "current_node_id": station_id,
            "visited_nodes": visited,
            "board_position": {"kind": "city", "node_id": station_id},
            "visited_board_cases": player["visited_board_cases"],
            "fuel": FUEL_CAPACITY_LITERS,
            "coins": max(0, player["coins"] - tow_cost),
            "durability": player["durability"],
            "repairs_needed": player["repairs_needed"],
            "distance_km": player["distance_km"],
            "completed_trajets": player["completed_trajets"],
            "xp": player["xp"],
            "victory_points": player["victory_points"],
            "dice_remaining": 0,
            "turn_roll": 0,
            "mission_locked_turns": player["mission_locked_turns"],
            "trajet_draws_long": player["trajet_draws_long"],
            "trajet_draws_short": player["trajet_draws_short"],
        }
        _update_session_player(conn, session["id"], user_id, progress)
        updated_session = finish_turn(conn, user_id, code, "tow", f"Depanneuse vers {station_id}")
        return {
            "move": {
                "from": player["current_node_id"],
                "to": station_id,
                "road": None,
                "route": None,
                "weather": "clear",
                "weather_fuel_cost": 0,
                "messages": [f"Panne d'essence: depanneuse vers {station_id}, plein fait, -{tow_cost} pieces."],
            },
            "event": None,
            "drawn": [],
            "tow": {"to": station_id, "cost": tow_cost},
            "session": updated_session,
            "progression": serialize_progression(get_progression(conn, user_id)),
        }
    if player["coins"] < total_coin_cost:
        raise ApiError(400, "Pas assez de pieces pour payer cette route.")

    visited = list(player["visited_nodes"])
    progress = _board_progress_from_player(player)
    progress["fuel"] -= total_fuel_cost
    progress["coins"] -= total_coin_cost
    progress["durability"] -= durability_cost
    progress["distance_km"] += steps * 100
    progress["dice_remaining"] = max(0, player["dice_remaining"] - steps)

    drawn = None
    feature_messages = list(modifier_messages)
    if arrived_city:
        progress["current_node_id"] = reached_node_id
        progress["board_position"] = {"kind": "city", "node_id": reached_node_id}
        if reached_node_id not in visited:
            visited.append(reached_node_id)
        progress["visited_nodes"] = visited
        city_state_row = conn.execute(
            "SELECT * FROM session_city_states WHERE session_id = ? AND node_id = ?",
            (session["id"], reached_node_id),
        ).fetchone()
        city_state = _serialize_city_state(city_state_row)
        if player["repairs_needed"] and city_state["feature_type"] != "garage":
            raise ApiError(400, "Panne active: rejoignez une ville garage avant de continuer.")
        worn_durability = progress["durability"]
        progress, feature_messages, drawn = _apply_city_feature(conn, session["id"], user_id, progress, city_state)
        if durability_cost > 0 and progress["durability"] > worn_durability:
            progress["durability"] = min(progress["durability"], MAX_DURABILITY - 1)
        if progress["dice_remaining"] > 0:
            reached_node = get_node(conn, reached_node_id)
            city_name = reached_node["city"] if reached_node else reached_node_id
            feature_messages.append(f"Arrivee a {city_name}: {progress['dice_remaining']} case(s) restantes. Continuez ou passez le tour pour rester.")
    else:
        progress["board_position"] = {
            "kind": "route",
            "route_id": route["id"],
            "from_node_id": route["from_node_id"],
            "to_node_id": route["to_node_id"],
            "target_node_id": target_node_id,
            "index": new_index,
            "case_count": route["case_count"],
            "x": board_case["x"],
            "y": board_case["y"],
            "case_kind": board_case["kind"],
        }
        feature_messages = _apply_board_case(progress, board_case)

    event_payload = None
    event = None
    if event:
        effect = json.loads(event["effect_json"])
        progress["xp"] += int(effect.get("xp", 0))
        progress["fuel"] += int(effect.get("fuel", 0))
        progress["coins"] += int(effect.get("coins", 0))
        progress["durability"] += int(effect.get("durability", 0))
        progress["repairs_needed"] += int(effect.get("repairs_needed", 0))
        event_payload = {
            "slug": event["slug"],
            "name": event["name"],
            "type": event["event_type"],
            "description": event["description"],
            "effect": effect,
        }

    delivered = _deliver_carpooler_if_needed(conn, session["id"], user_id, progress) if arrived_city else None
    claimed_contracts = _claim_public_contracts(conn, session, user_id, progress) if arrived_city else []
    for contract in claimed_contracts:
        feature_messages.append(f"Contrat public remporte: +{contract['reward_coins']} pieces, +{contract['reward_victory_points']} pts.")
    offered_carpooler = _maybe_offer_carpooler(conn, session["id"], user_id, progress["current_node_id"]) if arrived_city else None
    _maybe_start_closing(conn, session, user_id, progress)
    _update_session_player(conn, session["id"], user_id, progress)

    account = serialize_progression(get_progression(conn, user_id))
    account_visited = sorted(set(account["visited_nodes"]) | set(visited))
    account_row = update_progression(
        conn,
        user_id,
        current_node_id=progress["current_node_id"],
        visited_nodes=account_visited,
        distance_km=account["distance_km"] + steps * 100,
        fuel=progress["fuel"],
        coins=account["coins"],
        xp=account["xp"] + max(0, progress["xp"] - player["xp"]),
    )
    sync_unlocks_and_achievements(conn, user_id, account_row)
    if progress["dice_remaining"] <= 0:
        updated_session = finish_turn(conn, user_id, code, "move", f"{player['current_node_id']} -> {target_node_id}")
    else:
        updated_session = serialize_session(conn, _session_row(conn, code), user_id)
    return {
        "move": {
            "from": player["current_node_id"],
            "to": reached_node_id or target_node_id,
            "road": route,
            "route": route,
            "steps": steps,
            "case_index": new_index,
            "arrived_city": arrived_city,
            "weather": target["weather"],
            "weather_fuel_cost": 0,
            "durability_cost": durability_cost,
            "low_durability_fuel_penalty": low_durability_penalty,
            "messages": feature_messages,
        },
        "event": event_payload,
        "drawn": drawn or [],
        "carpooler": offered_carpooler,
        "delivered_carpooler": delivered,
        "claimed_contracts": claimed_contracts,
        "session": updated_session,
        "progression": serialize_progression(get_progression(conn, user_id)),
    }


def _active_task_entry(conn, session_id, user_id, difficulty=None):
    rows = conn.execute(
        "SELECT * FROM session_city_states WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    for row in rows:
        city_state = _serialize_city_state(row)
        for task in city_state["tasks"]:
            if not _is_user(task.get("active_by"), user_id):
                continue
            if difficulty and task["difficulty"] != difficulty:
                continue
            return row, city_state, task
    return None, None, None


def activate_task(conn, user_id, code, difficulty):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    if player["board_position"].get("kind") != "city":
        raise ApiError(400, "Les missions ne s'activent que dans une ville.")

    active_row, _, active_task = _active_task_entry(conn, session["id"], user_id)
    if active_task:
        if active_row["node_id"] == player["current_node_id"] and active_task["difficulty"] == difficulty:
            return {"task": active_task, "session": serialize_session(conn, session, user_id)}
        raise ApiError(400, "Vous avez deja une mission active.")

    city_state = _serialize_city_state(
        conn.execute(
            "SELECT * FROM session_city_states WHERE session_id = ? AND node_id = ?",
            (session["id"], player["current_node_id"]),
        ).fetchone()
    )
    task = next((item for item in city_state["tasks"] if item["difficulty"] == difficulty), None)
    if not task:
        raise ApiError(404, "Mission introuvable.")
    if task.get("completed_by"):
        raise ApiError(400, "Cette mission a deja ete realisee.")
    if task.get("active_by") and not _is_user(task.get("active_by"), user_id):
        raise ApiError(400, "Cette mission est deja prise.")

    for item in city_state["tasks"]:
        if item["difficulty"] == difficulty:
            item["active_by"] = user_id
    conn.execute(
        "UPDATE session_city_states SET tasks_json = ? WHERE id = ?",
        (json.dumps(city_state["tasks"]), city_state["id"]),
    )
    return {
        "task": task,
        "session": serialize_session(conn, session, user_id),
    }


def complete_task(conn, user_id, code, difficulty):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    row, city_state, task = _active_task_entry(conn, session["id"], user_id, difficulty)
    if not task:
        raise ApiError(404, "Activez cette mission avant de la realiser.")
    if task.get("completed_by"):
        raise ApiError(400, "Cette mission a deja ete realisee.")
    if task.get("mission_type") == "deplacement":
        target_node_id = task.get("target_node_id")
        if player["board_position"].get("kind") != "city" or player["current_node_id"] != target_node_id:
            raise ApiError(400, "Cette mission demande d'abord de rejoindre la ville voisine indiquee.")
    duration_turns = max(1, int(task.get("duration_turns", 1)))
    visited_nodes = list(player["visited_nodes"])
    progress = {
        "current_node_id": player["current_node_id"],
        "visited_nodes": visited_nodes,
        "board_position": player["board_position"],
        "visited_board_cases": player["visited_board_cases"],
        "fuel": player["fuel"],
        "coins": player["coins"] + int(task["reward_coins"]),
        "durability": player["durability"] + int(task.get("reward_durability", 0)),
        "repairs_needed": player["repairs_needed"],
        "distance_km": player["distance_km"],
        "completed_trajets": player["completed_trajets"],
        "xp": player["xp"] + int(task["reward_xp"]),
        "victory_points": player["victory_points"] + int(task.get("victory_points", 0)),
        "mission_locked_turns": max(0, duration_turns - 1),
        "trajet_draws_long": player["trajet_draws_long"],
        "trajet_draws_short": player["trajet_draws_short"],
    }
    teleport_target_id = task.get("target_node_id") if task.get("mission_type") in ("teleport_capital", "teleport_random") else None
    if teleport_target_id:
        target_node = get_node(conn, teleport_target_id)
        if not target_node:
            raise ApiError(404, "Destination de mission introuvable.")
        progress["current_node_id"] = teleport_target_id
        progress["board_position"] = {"kind": "city", "node_id": teleport_target_id}
        progress["dice_remaining"] = 0
        progress["turn_roll"] = 0
        if teleport_target_id not in progress["visited_nodes"]:
            progress["visited_nodes"].append(teleport_target_id)
    if task.get("double_die"):
        progress["dice_remaining"] = 12
        progress["turn_roll"] = 12
        progress["mission_locked_turns"] = 0
    penalty = None
    if random.random() < float(task["risk"]):
        if difficulty == "dur":
            progress["durability"] = max(0, progress["durability"] - 12)
            penalty = "La mission express a use la Twingo."
        else:
            progress["durability"] = max(0, progress["durability"] - 5)
            penalty = "La mission a use un peu plus la Twingo."
    for item in city_state["tasks"]:
        if item["difficulty"] == difficulty:
            item["completed_by"] = user_id
            item["active_by"] = None
    conn.execute(
        "UPDATE session_city_states SET tasks_json = ? WHERE id = ?",
        (json.dumps(city_state["tasks"]), row["id"]),
    )
    _maybe_start_closing(conn, session, user_id, progress)
    _update_session_player(conn, session["id"], user_id, progress)

    account = serialize_progression(get_progression(conn, user_id))
    account_visited = sorted(set(account["visited_nodes"]) | set(progress["visited_nodes"]))
    account_row = update_progression(
        conn,
        user_id,
        xp=account["xp"] + int(task["reward_xp"]),
        coins=account["coins"],
        successful_events=account["successful_events"] + 1,
        fuel=progress["fuel"],
        current_node_id=progress["current_node_id"],
        visited_nodes=account_visited,
    )
    sync_unlocks_and_achievements(conn, user_id, account_row)
    if task.get("double_die"):
        updated_session = serialize_session(conn, _session_row(conn, code), user_id)
    else:
        updated_session = finish_turn(conn, user_id, code, "task", task["title"])
    return {
        "task": task,
        "penalty": penalty,
        "session": updated_session,
        "progression": serialize_progression(get_progression(conn, user_id)),
    }


def use_city_service(conn, user_id, code, service_type):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    if player["board_position"].get("kind") != "city":
        raise ApiError(400, "Ce service n'est disponible que dans une ville.")
    city_state = _serialize_city_state(
        conn.execute(
            "SELECT * FROM session_city_states WHERE session_id = ? AND node_id = ?",
            (session["id"], player["current_node_id"]),
        ).fetchone()
    )
    is_capital = player["current_node_id"] in CAPITAL_NODE_IDS
    if service_type == "station":
        allowed = is_capital or city_state["feature_type"] == "station"
    else:
        allowed = is_capital or city_state["feature_type"] == "garage"
    if not allowed:
        raise ApiError(400, "Ce service n'est pas disponible dans cette ville.")
    payload = city_state["feature_payload"]
    progress = {
        "current_node_id": player["current_node_id"],
        "visited_nodes": player["visited_nodes"],
        "fuel": player["fuel"],
        "coins": player["coins"],
        "durability": player["durability"],
        "repairs_needed": player["repairs_needed"],
        "distance_km": player["distance_km"],
        "completed_trajets": player["completed_trajets"],
        "xp": player["xp"],
        "victory_points": player["victory_points"],
        "mission_locked_turns": player["mission_locked_turns"],
        "trajet_draws_long": player["trajet_draws_long"],
        "trajet_draws_short": player["trajet_draws_short"],
    }
    if service_type == "station":
        price = int(payload.get("fuel_price", 18))
        if progress["fuel"] >= FUEL_CAPACITY_LITERS:
            return {"summary": "Le reservoir est deja plein.", "session": serialize_session(conn, session, user_id)}
        if progress["coins"] < price:
            raise ApiError(400, "Pas assez de pieces pour le plein.")
        progress["coins"] -= price
        progress["fuel"] = FUEL_CAPACITY_LITERS
        summary = f"Plein effectue pour {price} pieces."
    else:
        price = int(payload.get("repair_price", 26))
        if progress["repairs_needed"] <= 0 and progress["durability"] >= MAX_DURABILITY:
            summary = "Aucune reparation necessaire."
        else:
            if progress["coins"] < price:
                raise ApiError(400, "Pas assez de pieces pour reparer.")
            progress["coins"] -= price
            progress["repairs_needed"] = 0
            progress["durability"] = MAX_DURABILITY
            _resolve_mechanical_malus(conn, session["id"], user_id, "any")
            summary = f"Reparation et durabilite restaurees pour {price} pieces."
    _update_session_player(conn, session["id"], user_id, progress)
    return {"summary": summary, "session": serialize_session(conn, session, user_id)}


def player_interaction(conn, user_id, code, target_user_id, interaction_type):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        raise ApiError(400, "Joueur cible invalide.")
    if target_user_id == user_id:
        raise ApiError(400, "Choisissez un autre joueur.")
    target_row = _membership(conn, session["id"], target_user_id)
    if not target_row:
        raise ApiError(404, "Ce joueur n'est pas dans la partie.")
    actor = _serialize_player(_membership(conn, session["id"], user_id))
    target = _serialize_player(target_row)
    actor_progress = _board_progress_from_player(actor)
    target_progress = _board_progress_from_player(target)

    if interaction_type == "gift_coins":
        amount = 10
        if actor_progress["coins"] < amount:
            raise ApiError(400, "Pas assez de pieces pour aider ce joueur.")
        actor_progress["coins"] -= amount
        target_progress["coins"] += amount
        summary = f"{actor['display_name']} offre {amount} pieces a {target['display_name']}."
    elif interaction_type == "gift_fuel":
        amount = 5
        if actor_progress["fuel"] < amount:
            raise ApiError(400, "Pas assez d'essence pour partager.")
        actor_progress["fuel"] -= amount
        target_progress["fuel"] = min(FUEL_CAPACITY_LITERS, target_progress["fuel"] + amount)
        summary = f"{actor['display_name']} offre {amount}L d'essence a {target['display_name']}."
    elif interaction_type == "twingo_challenge":
        stake = 10
        if actor_progress["coins"] < stake:
            raise ApiError(400, "Il faut 10 pieces pour lancer un defi Twingo.")
        actor_roll = random.randint(1, 6)
        target_roll = random.randint(1, 6)
        actor_progress["coins"] -= stake
        if actor_roll >= target_roll:
            actor_progress["coins"] += 25
            actor_progress["victory_points"] += 2
            summary = f"Defi Twingo: {actor['display_name']} gagne {actor_roll}-{target_roll}, +15 pieces nettes et +2 pts."
        else:
            target_progress["coins"] += 15
            summary = f"Defi Twingo: {target['display_name']} gagne {target_roll}-{actor_roll}, +15 pieces."
    else:
        raise ApiError(400, "Interaction inconnue.")

    _update_session_player(conn, session["id"], user_id, actor_progress)
    _update_session_player(conn, session["id"], target_user_id, target_progress)
    conn.execute(
        "INSERT INTO session_turn_logs (session_id, user_id, action_type, summary) VALUES (?, ?, 'interaction', ?)",
        (session["id"], user_id, summary),
    )
    return {"summary": summary, "session": serialize_session(conn, _session_row(conn, code), user_id)}


def apply_session_special_card(conn, user_id, code, inventory_id):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, inventory.quantity, cards.*
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ? AND inventory.id = ? AND inventory.item_type = 'card'
        """,
        (user_id, inventory_id),
    ).fetchone()
    if not row:
        raise ApiError(404, "Carte introuvable.")
    if row["type"] == "trajet":
        raise ApiError(400, "Les cartes Trajet se valident avec l'objectif de villes.")
    if row["status"] != "active":
        raise ApiError(400, "Cette carte n'est plus active.")

    effect = json.loads(row["effect_json"] or "{}")
    if effect.get("requires_capital_fine"):
        fine = int(effect["requires_capital_fine"])
        target_capital_id = player["current_node_id"] if player["current_node_id"] in CAPITAL_NODE_IDS else _nearest_capital_id(conn, player["current_node_id"])
        if player["board_position"].get("kind") != "city" or player["current_node_id"] != target_capital_id:
            raise ApiError(409, f"Amende a regler dans la capitale la plus proche: {target_capital_id}.")
        if player["coins"] < fine:
            raise ApiError(400, f"Il faut {fine} gold pour regler cette amende.")

    if effect.get("requires_garage_repair") and not _is_repair_city(conn, session["id"], player):
        raise ApiError(409, "Rendez-vous dans un garage ou une capitale pour reparer ce malus.")

    progress = _board_progress_from_player(player)
    progress["fuel"] += int(effect.get("fuel", 0))
    progress["coins"] += int(effect.get("coins", 0))
    progress["durability"] += int(effect.get("durability", 0))
    progress["repairs_needed"] += int(effect.get("repairs_needed", 0))
    progress["xp"] += int(effect.get("xp", 0))
    progress["dice_remaining"] = max(0, progress["dice_remaining"] + int(effect.get("dice_remaining", 0)))
    progress["turn_roll"] = max(progress["turn_roll"], progress["dice_remaining"])
    progress["mission_locked_turns"] = max(progress["mission_locked_turns"], int(effect.get("skip_turns", 0)))

    if effect.get("fuel_percent"):
        progress["fuel"] = max(0, round(progress["fuel"] * (100 + int(effect["fuel_percent"])) / 100))
    if effect.get("fuel_capacity_percent"):
        progress["fuel"] += round(FUEL_CAPACITY_LITERS * int(effect["fuel_capacity_percent"]) / 100)
    if effect.get("requires_capital_fine"):
        progress["coins"] -= int(effect["requires_capital_fine"])

    resolved_mechanics = []
    if effect.get("resolve_mechanical"):
        resolved_mechanics = _resolve_mechanical_malus(conn, session["id"], user_id, effect["resolve_mechanical"])
        if not resolved_mechanics and effect["resolve_mechanical"] != "any":
            raise ApiError(400, "Aucun malus mecanique correspondant a annuler.")
    if effect.get("requires_garage_repair"):
        resolved_mechanics = _resolve_mechanical_malus(conn, session["id"], user_id, effect.get("mechanical_malus", "any"))
        progress["repairs_needed"] = 0

    if effect.get("coins_from_each_player"):
        gift = int(effect["coins_from_each_player"])
        others = conn.execute(
            "SELECT user_id, coins FROM session_players WHERE session_id = ? AND user_id != ?",
            (session["id"], user_id),
        ).fetchall()
        total = 0
        for other in others:
            paid = min(gift, int(other["coins"]))
            if paid:
                conn.execute(
                    "UPDATE session_players SET coins = coins - ? WHERE session_id = ? AND user_id = ?",
                    (paid, session["id"], other["user_id"]),
                )
                total += paid
        progress["coins"] += total

    if effect.get("steal_gold_random"):
        amount = int(effect["steal_gold_random"])
        victim = conn.execute(
            "SELECT user_id, coins FROM session_players WHERE session_id = ? AND user_id != ? AND coins > 0 ORDER BY RANDOM() LIMIT 1",
            (session["id"], user_id),
        ).fetchone()
        if victim:
            stolen = min(amount, int(victim["coins"]))
            conn.execute(
                "UPDATE session_players SET coins = coins - ? WHERE session_id = ? AND user_id = ?",
                (stolen, session["id"], victim["user_id"]),
            )
            progress["coins"] += stolen

    if effect.get("turns") and (effect.get("fuel_multiplier") or effect.get("fuel_discount_percent")):
        conn.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (max(1, int(effect["turns"])), inventory_id))
    else:
        conn.execute("UPDATE inventory SET status = 'completed' WHERE id = ?", (inventory_id,))
    _update_session_player(conn, session["id"], user_id, progress)

    account = serialize_progression(get_progression(conn, user_id))
    account_row = update_progression(
        conn,
        user_id,
        xp=account["xp"] + int(effect.get("xp", 0)),
        coins=0,
        successful_events=account["successful_events"] + int(effect.get("successful_events", 0)),
    )
    sync_unlocks_and_achievements(conn, user_id, account_row)
    return {
        "applied": row["name"],
        "effect": effect,
        "resolved_mechanics": resolved_mechanics,
        "progression": serialize_progression(get_progression(conn, user_id)),
        "inventory": get_user_inventory(conn, user_id),
        "session": serialize_session(conn, session, user_id),
    }


def draw_turn_cards(conn, user_id, code, count=3):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    raise ApiError(400, "Les bonus/malus se piochent automatiquement en passant sur une ville bonus/malus.")


def draw_turn_trajets(conn, user_id, code):
    session = get_session_or_error(conn, user_id, code)
    _require_playable_turn(conn, session, user_id)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    if player["trajet_draws_long"] or player["trajet_draws_short"]:
        raise ApiError(400, "Vous avez deja pioche vos trajets ce tour.")
    cards = draw_session_trajet_cards(conn, user_id, session["id"], long_count=1, short_count=2)
    conn.execute(
        """
        UPDATE session_players
        SET trajet_draws_long = 1, trajet_draws_short = 2, dice_remaining = 0, turn_roll = 0
        WHERE session_id = ? AND user_id = ?
        """,
        (session["id"], user_id),
    )
    updated_session = finish_turn(conn, user_id, code, "draw_trajets", "Pioche trajet: 1 long et 2 courts")
    return {**cards, "session": updated_session}


def discard_session_trajet(conn, user_id, code, inventory_id):
    session = get_session_or_error(conn, user_id, code)
    player = _serialize_player(_membership(conn, session["id"], user_id))
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, cards.name, cards.type
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ? AND inventory.id = ? AND inventory.item_type = 'card'
        """,
        (user_id, inventory_id),
    ).fetchone()
    if not row:
        raise ApiError(404, "Carte introuvable.")
    if row["type"] != "trajet":
        raise ApiError(400, "Seules les cartes Trajet peuvent etre abandonnees.")
    if row["status"] != "active":
        raise ApiError(400, "Cette carte Trajet n'est plus active.")
    progression = serialize_progression(get_progression(conn, user_id))
    cost = 20 + progression["level"] * 10
    if player["coins"] < cost:
        raise ApiError(400, f"Il faut {cost} pieces dans la partie pour abandonner ce trajet.")
    conn.execute("UPDATE inventory SET status = 'discarded' WHERE id = ?", (inventory_id,))
    conn.execute(
        "UPDATE session_players SET coins = coins - ?, last_action_at = CURRENT_TIMESTAMP WHERE session_id = ? AND user_id = ?",
        (cost, session["id"], user_id),
    )
    return {
        "discarded": row["name"],
        "cost": cost,
        "inventory": get_user_inventory(conn, user_id),
        "progression": serialize_progression(get_progression(conn, user_id)),
        "session": serialize_session(conn, session, user_id),
    }


def accept_carpooler(conn, user_id, code, carpooler_id):
    session = get_session_or_error(conn, user_id, code)
    if session["status"] not in ("active", "closing"):
        raise ApiError(409, "La partie n'est pas lancee.")
    player = _serialize_player(_membership(conn, session["id"], user_id))
    row = conn.execute(
        "SELECT * FROM session_carpoolers WHERE session_id = ? AND id = ? AND status = 'waiting'",
        (session["id"], carpooler_id),
    ).fetchone()
    if not row:
        raise ApiError(404, "Covoitureur indisponible.")
    if player["board_position"].get("kind") != "city" or player["current_node_id"] != row["start_node_id"]:
        raise ApiError(400, "Vous devez rencontrer ce covoitureur dans sa ville de depart.")
    if player["mission_locked_turns"] > 0:
        raise ApiError(409, "Mission en cours: impossible de prendre un covoitureur.")
    active = conn.execute(
        "SELECT 1 FROM session_carpoolers WHERE session_id = ? AND assigned_user_id = ? AND status = 'active'",
        (session["id"], user_id),
    ).fetchone()
    if active:
        raise ApiError(400, "Vous transportez deja un covoitureur.")
    conn.execute(
        "UPDATE session_carpoolers SET status = 'active', assigned_user_id = ? WHERE id = ?",
        (user_id, carpooler_id),
    )
    return serialize_session(conn, session, user_id)


def complete_session_trajet(conn, user_id, code, inventory_id):
    session = get_session_or_error(conn, user_id, code)
    before = _serialize_player(_membership(conn, session["id"], user_id))
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, cards.name, cards.type, cards.trajet_id,
               trajets.city_ids_json, trajets.title, trajets.distance_hint, trajets.reward_xp, trajets.reward_coins
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        JOIN trajets ON trajets.id = cards.trajet_id
        WHERE inventory.user_id = ? AND inventory.id = ? AND inventory.item_type = 'card'
        """,
        (user_id, inventory_id),
    ).fetchone()
    if not row:
        raise ApiError(404, "Carte Trajet introuvable.")
    if row["type"] != "trajet":
        raise ApiError(400, "Cette carte n'est pas une carte Trajet.")
    if row["status"] == "completed":
        raise ApiError(400, "Cette carte est deja completee.")
    if row["status"] != "active":
        raise ApiError(400, "Cette carte Trajet n'est plus active.")

    required = set(json.loads(row["city_ids_json"] or "[]"))
    missing = sorted(required - set(before["visited_nodes"]))
    if missing:
        raise ApiError(400, "Trajet incomplet.", {"missing_city_ids": missing})

    conn.execute("UPDATE inventory SET status = 'completed' WHERE id = ?", (inventory_id,))
    conn.execute(
        """
        INSERT INTO trip_history (user_id, trajet_id, title, distance_km, reward_xp, reward_coins)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, row["trajet_id"], row["title"], row["distance_hint"], row["reward_xp"], row["reward_coins"]),
    )
    account = serialize_progression(get_progression(conn, user_id))
    account_row = update_progression(
        conn,
        user_id,
        xp=account["xp"] + row["reward_xp"],
        coins=account["coins"],
        completed_trajets=account["completed_trajets"] + 1,
    )
    account_row = sync_unlocks_and_achievements(conn, user_id, account_row)

    distance = row["distance_hint"]
    points = max(5, min(30, round(distance / 120)))
    progress = {
        "current_node_id": before["current_node_id"],
        "visited_nodes": before["visited_nodes"],
        "fuel": before["fuel"],
        "coins": before["coins"],
        "durability": before["durability"],
        "repairs_needed": before["repairs_needed"],
        "distance_km": before["distance_km"],
        "completed_trajets": before["completed_trajets"] + 1,
        "xp": before["xp"] + row["reward_xp"],
        "victory_points": before["victory_points"] + points,
        "mission_locked_turns": before["mission_locked_turns"],
        "trajet_draws_long": before["trajet_draws_long"],
        "trajet_draws_short": before["trajet_draws_short"],
    }
    _maybe_start_closing(conn, session, user_id, progress)
    _update_session_player(conn, session["id"], user_id, progress)
    return {
        "completed": row["title"],
        "progression": serialize_progression(account_row),
        "inventory": get_user_inventory(conn, user_id),
        "victory_points": points,
        "session": serialize_session(conn, _session_row(conn, code), user_id),
    }
