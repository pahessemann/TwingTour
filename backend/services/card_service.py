import json
import random

from backend.models.errors import ApiError
from backend.services.progression_service import apply_effect, get_progression, serialize_progression, sync_unlocks_and_achievements, update_progression


def _serialize_card(row, trajet=None, inventory_id=None, status=None):
    card = dict(row)
    card["effect"] = json.loads(card.pop("effect_json") or "{}")
    if trajet:
        card["trajet"] = _serialize_trajet(trajet)
    if inventory_id is not None:
        card["inventory_id"] = inventory_id
    if status is not None:
        card["status"] = status
    return card


def _serialize_trajet(row):
    trajet = dict(row)
    trajet["city_ids"] = json.loads(trajet.pop("city_ids_json") or "[]")
    return trajet


def get_catalog(conn):
    cards = []
    for row in conn.execute("SELECT * FROM cards ORDER BY type DESC, id").fetchall():
        trajet = conn.execute("SELECT * FROM trajets WHERE id = ?", (row["trajet_id"],)).fetchone() if row["trajet_id"] else None
        cards.append(_serialize_card(row, trajet))
    skins = []
    for skin in conn.execute("SELECT * FROM skins ORDER BY min_level, id").fetchall():
        data = dict(skin)
        data["palette"] = json.loads(data.pop("palette_json") or "[]")
        skins.append(data)
    return {"cards": cards, "skins": skins}


def get_user_inventory(conn, user_id):
    inventory_cards = []
    rows = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.session_id, inventory.status, inventory.quantity, cards.*
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ? AND inventory.item_type = 'card'
        ORDER BY inventory.created_at DESC, inventory.id DESC
        """,
        (user_id,),
    ).fetchall()
    for row in rows:
        trajet = conn.execute("SELECT * FROM trajets WHERE id = ?", (row["trajet_id"],)).fetchone() if row["trajet_id"] else None
        inventory_cards.append(_serialize_card(row, trajet, row["inventory_id"], row["status"]))
    return inventory_cards


def _inventory_card(conn, inventory_id):
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.session_id, inventory.status, inventory.quantity, cards.*
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.id = ? AND inventory.item_type = 'card'
        """,
        (inventory_id,),
    ).fetchone()
    if not row:
        return None
    trajet = conn.execute("SELECT * FROM trajets WHERE id = ?", (row["trajet_id"],)).fetchone() if row["trajet_id"] else None
    return _serialize_card(row, trajet, row["inventory_id"], row["status"])


def draw_cards(conn, user_id, count=3):
    active_trajet_ids = {
        row["item_id"]
        for row in conn.execute(
            """
            SELECT cards.id AS item_id
            FROM inventory
            JOIN cards ON cards.id = inventory.item_id
            WHERE inventory.user_id = ?
              AND inventory.item_type = 'card'
              AND cards.type = 'trajet'
              AND inventory.status IN ('active', 'completed')
            """,
            (user_id,),
        ).fetchall()
    }
    candidates = conn.execute("SELECT * FROM cards").fetchall()
    weighted = []
    for card in candidates:
        if card["type"] == "trajet" and card["id"] in active_trajet_ids:
            continue
        weight = 3 if card["type"] == "trajet" else 2
        weighted.extend([card] * weight)
    if not weighted:
        raise ApiError(400, "Aucune carte disponible a tirer.")

    drawn = []
    picked_ids = set()
    while weighted and len(drawn) < count:
        card = random.choice(weighted)
        if card["type"] == "trajet" and card["id"] in picked_ids:
            weighted = [candidate for candidate in weighted if candidate["id"] != card["id"]]
            continue
        picked_ids.add(card["id"])
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'card', ?, 'active')",
            (user_id, card["id"]),
        )
        trajet = conn.execute("SELECT * FROM trajets WHERE id = ?", (card["trajet_id"],)).fetchone() if card["trajet_id"] else None
        drawn.append(_serialize_card(card, trajet, cursor.lastrowid, "active"))
        if card["type"] == "trajet":
            weighted = [candidate for candidate in weighted if candidate["id"] != card["id"]]
    return {"drawn": drawn, "inventory": get_user_inventory(conn, user_id)}


def draw_special_cards(conn, user_id, count=1, session_id=None):
    candidates = conn.execute("SELECT * FROM cards WHERE type IN ('bonus', 'malus') ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
    drawn = []
    for card in candidates:
        effect = json.loads(card["effect_json"] or "{}")
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, session_id, item_type, item_id, quantity, status) VALUES (?, ?, 'card', ?, ?, 'active')",
            (user_id, session_id, card["id"], max(1, int(effect.get("turns", 1)))),
        )
        drawn.append(_serialize_card(card, None, cursor.lastrowid, "active"))
    return {"drawn": drawn, "inventory": get_user_inventory(conn, user_id)}


def active_trajet_count(conn, user_id, session_id=None):
    session_filter = "AND inventory.session_id = ?" if session_id is not None else ""
    params = (user_id, session_id) if session_id is not None else (user_id,)
    return conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ?
          AND inventory.item_type = 'card'
          AND cards.type = 'trajet'
          AND inventory.status = 'active'
          {session_filter}
        """,
        params,
    ).fetchone()["count"]


def _session_used_trajet_card_ids(conn, session_id):
    return {
        row["card_id"]
        for row in conn.execute(
            """
            SELECT DISTINCT cards.id AS card_id
            FROM session_players
            JOIN inventory ON inventory.user_id = session_players.user_id
            JOIN cards ON cards.id = inventory.item_id
            WHERE session_players.session_id = ?
              AND inventory.item_type = 'card'
              AND inventory.session_id = ?
              AND cards.type = 'trajet'
              AND inventory.status IN ('active', 'completed', 'choice')
            """,
            (session_id, session_id),
        ).fetchall()
    }


def get_starting_trajet_choices(conn, user_id, session_id):
    rows = conn.execute(
        """
        SELECT inventory.id AS inventory_id
        FROM inventory
        JOIN cards ON cards.id = inventory.item_id
        WHERE inventory.user_id = ?
          AND inventory.session_id = ?
          AND inventory.item_type = 'card'
          AND cards.type = 'trajet'
          AND inventory.status = 'choice'
        ORDER BY inventory.id
        """,
        (user_id, session_id),
    ).fetchall()
    return [card for card in (_inventory_card(conn, row["inventory_id"]) for row in rows) if card]


def _trajet_candidates(conn, kind):
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT cards.id AS card_id, trajets.city_ids_json
            FROM cards
            JOIN trajets ON trajets.id = cards.trajet_id
            WHERE cards.type = 'trajet' AND trajets.kind = ?
            ORDER BY RANDOM()
            """,
            (kind,),
        ).fetchall()
    ]


def _city_ids(candidate):
    return json.loads(candidate["city_ids_json"] or "[]")


def _pick_trajet(candidates, picked_ids, used_ids, predicate=None):
    for candidate in candidates:
        card_id = candidate["card_id"]
        if card_id in picked_ids or card_id in used_ids:
            continue
        city_ids = _city_ids(candidate)
        if predicate and not predicate(city_ids):
            continue
        picked_ids.add(card_id)
        return card_id
    return None


def _create_spawn_starter_card(conn, spawn_node_id):
    origin = conn.execute("SELECT * FROM map_nodes WHERE id = ?", (spawn_node_id,)).fetchone()
    if not origin:
        return None
    destinations = conn.execute(
        """
        SELECT *, ((x - ?) * (x - ?) + (y - ?) * (y - ?)) AS distance_score
        FROM map_nodes
        WHERE id != ?
        ORDER BY distance_score
        LIMIT 12
        """,
        (origin["x"], origin["x"], origin["y"], origin["y"], spawn_node_id),
    ).fetchall()
    for destination in destinations:
        base_title = f"{origin['city']} -> {destination['city']}"
        suffix = 1
        title = base_title
        slug = f"trajet-starter-{spawn_node_id.lower()}-{destination['id'].lower()}"
        while conn.execute("SELECT 1 FROM trajets WHERE title = ?", (title,)).fetchone() or conn.execute("SELECT 1 FROM cards WHERE slug = ?", (slug,)).fetchone():
            suffix += 1
            title = f"{base_title} depart {suffix}"
            slug = f"trajet-starter-{spawn_node_id.lower()}-{destination['id'].lower()}-{suffix}"
        distance_hint = max(120, min(760, round((float(destination["distance_score"]) ** 0.5) * 3)))
        trajet_cursor = conn.execute(
            """
            INSERT INTO trajets (title, kind, city_ids_json, distance_hint, reward_xp, reward_coins, description)
            VALUES (?, 'court', ?, ?, ?, ?, ?)
            """,
            (
                title,
                json.dumps([spawn_node_id, destination["id"]]),
                distance_hint,
                max(45, min(120, round(distance_hint / 5))),
                max(22, min(58, round(distance_hint / 12))),
                "Trajet facile de depart genere pour cette partie.",
            ),
        )
        card_cursor = conn.execute(
            """
            INSERT INTO cards (slug, type, name, rarity, description, effect_json, trajet_id)
            VALUES (?, 'trajet', ?, 'Court', ?, ?, ?)
            """,
            (
                slug,
                title,
                "Trajet facile de depart depuis votre capitale.",
                json.dumps({"required_cities": [spawn_node_id, destination["id"]]}),
                trajet_cursor.lastrowid,
            ),
        )
        return card_cursor.lastrowid
    return None


def setup_initial_trajet_choices(conn, user_id, session_id, spawn_node_id):
    conn.execute(
        """
        UPDATE inventory
        SET status = 'archived'
        WHERE user_id = ?
          AND item_type = 'card'
          AND status IN ('active', 'choice')
          AND (session_id = ? OR session_id IS NULL)
        """,
        (user_id, session_id),
    )
    used_ids = _session_used_trajet_card_ids(conn, session_id)
    picked_ids = set()
    chosen_card_ids = []
    short_candidates = _trajet_candidates(conn, "court")
    long_candidates = _trajet_candidates(conn, "long")

    spawn_card_id = _pick_trajet(
        short_candidates,
        picked_ids,
        used_ids,
        lambda city_ids: bool(city_ids) and city_ids[0] == spawn_node_id,
    )
    if not spawn_card_id:
        spawn_card_id = _pick_trajet(
            short_candidates,
            picked_ids,
            used_ids,
            lambda city_ids: spawn_node_id in city_ids,
        )
    if not spawn_card_id:
        spawn_card_id = _create_spawn_starter_card(conn, spawn_node_id)
        if spawn_card_id:
            picked_ids.add(spawn_card_id)
    if spawn_card_id:
        chosen_card_ids.append(spawn_card_id)

    while len([card_id for card_id in chosen_card_ids if card_id]) < 3:
        card_id = _pick_trajet(short_candidates, picked_ids, used_ids)
        if not card_id:
            break
        chosen_card_ids.append(card_id)

    while len(chosen_card_ids) < 5:
        kind_candidates = long_candidates if len(chosen_card_ids) >= 3 else short_candidates
        card_id = _pick_trajet(kind_candidates, picked_ids, used_ids)
        if not card_id and kind_candidates is long_candidates:
            card_id = _pick_trajet(short_candidates, picked_ids, used_ids)
        if not card_id:
            break
        chosen_card_ids.append(card_id)

    if len(chosen_card_ids) < 5:
        raise ApiError(400, "Pas assez de cartes Trajet disponibles pour preparer le depart.")

    choices = []
    for card_id in chosen_card_ids:
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, session_id, item_type, item_id, status) VALUES (?, ?, 'card', ?, 'choice')",
            (user_id, session_id, card_id),
        )
        choices.append(_inventory_card(conn, cursor.lastrowid))
        used_ids.add(card_id)
    return choices


def choose_initial_trajets(conn, user_id, session_id, inventory_ids):
    selected_ids = [int(inventory_id) for inventory_id in inventory_ids]
    if len(selected_ids) != 3 or len(set(selected_ids)) != 3:
        raise ApiError(400, "Choisissez exactement 3 cartes Trajet de depart.")
    choices = {
        row["inventory_id"]: row
        for row in conn.execute(
            """
            SELECT inventory.id AS inventory_id
            FROM inventory
            JOIN cards ON cards.id = inventory.item_id
            WHERE inventory.user_id = ?
              AND inventory.session_id = ?
              AND inventory.item_type = 'card'
              AND cards.type = 'trajet'
              AND inventory.status = 'choice'
            """,
            (user_id, session_id),
        ).fetchall()
    }
    if len(choices) < 5:
        raise ApiError(409, "Aucun choix de trajets de depart n'est en attente.")
    if any(inventory_id not in choices for inventory_id in selected_ids):
        raise ApiError(400, "Une des cartes choisies n'est pas disponible.")

    placeholders = ",".join("?" for _ in selected_ids)
    conn.execute(
        f"UPDATE inventory SET status = 'active' WHERE user_id = ? AND session_id = ? AND id IN ({placeholders})",
        (user_id, session_id, *selected_ids),
    )
    conn.execute(
        f"""
        UPDATE inventory
        SET status = 'archived'
        WHERE user_id = ?
          AND session_id = ?
          AND item_type = 'card'
          AND status = 'choice'
          AND id NOT IN ({placeholders})
        """,
        (user_id, session_id, *selected_ids),
    )
    return {
        "chosen": [card for card in (_inventory_card(conn, inventory_id) for inventory_id in selected_ids) if card],
        "inventory": get_user_inventory(conn, user_id),
    }


def _draw_trajets_by_kind(conn, user_id, session_id, kind, count):
    used_ids = _session_used_trajet_card_ids(conn, session_id)
    rows = conn.execute(
        """
        SELECT cards.id AS card_id
        FROM cards
        JOIN trajets ON trajets.id = cards.trajet_id
        WHERE cards.type = 'trajet' AND trajets.kind = ?
        ORDER BY RANDOM()
        """,
        (kind,),
    ).fetchall()
    drawn = []
    for row in rows:
        if len(drawn) >= count:
            break
        if row["card_id"] in used_ids:
            continue
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, session_id, item_type, item_id, status) VALUES (?, ?, 'card', ?, 'active')",
            (user_id, session_id, row["card_id"]),
        )
        card = conn.execute("SELECT * FROM cards WHERE id = ?", (row["card_id"],)).fetchone()
        trajet = conn.execute("SELECT * FROM trajets WHERE id = ?", (card["trajet_id"],)).fetchone()
        drawn.append(_serialize_card(card, trajet, cursor.lastrowid, "active"))
        used_ids.add(row["card_id"])
    return drawn


def draw_session_trajet_cards(conn, user_id, session_id, long_count=1, short_count=2):
    active_count = active_trajet_count(conn, user_id, session_id)
    if active_count >= 3:
        raise ApiError(400, "Vous avez deja 3 trajets actifs. Terminez-en un ou abandonnez-en un contre des pieces.")
    free_slots = 3 - active_count
    target_long = min(long_count, free_slots)
    target_short = min(short_count, free_slots - target_long)
    drawn = []
    drawn.extend(_draw_trajets_by_kind(conn, user_id, session_id, "long", target_long))
    drawn.extend(_draw_trajets_by_kind(conn, user_id, session_id, "court", target_short))
    if len(drawn) < free_slots and target_short:
        drawn.extend(_draw_trajets_by_kind(conn, user_id, session_id, "long", free_slots - len(drawn)))
    return {"drawn": drawn, "inventory": get_user_inventory(conn, user_id)}


def discard_trajet_card(conn, user_id, inventory_id):
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, cards.*
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
    cost = 0
    conn.execute("UPDATE inventory SET status = 'discarded' WHERE id = ?", (inventory_id,))
    return {"discarded": row["name"], "cost": cost, "inventory": get_user_inventory(conn, user_id), "progression": serialize_progression(get_progression(conn, user_id))}


def complete_trajet_card(conn, user_id, inventory_id):
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, cards.*, trajets.city_ids_json,
               trajets.title, trajets.distance_hint, trajets.reward_xp, trajets.reward_coins
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

    required = set(json.loads(row["city_ids_json"]))
    progress = serialize_progression(get_progression(conn, user_id))
    missing = sorted(required - set(progress["visited_nodes"]))
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
    progress_row = update_progression(
        conn,
        user_id,
        xp=progress["xp"] + row["reward_xp"],
        coins=0,
        completed_trajets=progress["completed_trajets"] + 1,
    )
    progress_row = sync_unlocks_and_achievements(conn, user_id, progress_row)
    return {
        "completed": row["title"],
        "progression": serialize_progression(progress_row),
        "inventory": get_user_inventory(conn, user_id),
    }


def apply_special_card(conn, user_id, inventory_id):
    row = conn.execute(
        """
        SELECT inventory.id AS inventory_id, inventory.status, cards.*
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
    progress_row = apply_effect(conn, user_id, effect)
    conn.execute("UPDATE inventory SET status = 'completed' WHERE id = ?", (inventory_id,))
    return {
        "applied": row["name"],
        "effect": effect,
        "progression": serialize_progression(progress_row),
        "inventory": get_user_inventory(conn, user_id),
    }


def get_history(conn, user_id):
    return [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM trip_history WHERE user_id = ? ORDER BY completed_at DESC",
            (user_id,),
        ).fetchall()
    ]
