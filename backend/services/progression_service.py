import json


FUEL_CAPACITY_LITERS = 35
DEFAULT_SKIN_SLUG = "twingo-bleu-mediterranee"
LEVEL_DISTANCE_CAPS = (1000, 2500, 5000)


def level_distance_cap(level):
    safe_level = max(1, int(level))
    if safe_level <= len(LEVEL_DISTANCE_CAPS):
        return LEVEL_DISTANCE_CAPS[safe_level - 1]
    return LEVEL_DISTANCE_CAPS[-1] * (2 ** (safe_level - len(LEVEL_DISTANCE_CAPS)))


def compute_level(distance_km):
    distance = max(0, int(distance_km))
    level = 1
    while distance >= level_distance_cap(level):
        level += 1
    return level


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def serialize_progression(row):
    data = dict(row)
    for key in ("visited_nodes_json", "unlocked_skins_json", "achievements_json"):
        data[key.replace("_json", "")] = json.loads(data.pop(key) or "[]")
    data["next_level_distance_km"] = level_distance_cap(data["level"])
    return data


def get_progression(conn, user_id):
    return conn.execute("SELECT * FROM progression WHERE user_id = ?", (user_id,)).fetchone()


def update_progression(conn, user_id, **changes):
    current = serialize_progression(get_progression(conn, user_id))
    merged = {**current, **changes}
    merged["level"] = compute_level(merged["distance_km"])
    merged["coins"] = 0
    conn.execute(
        """
        UPDATE progression
        SET level = ?, xp = ?, completed_trajets = ?, successful_events = ?, distance_km = ?,
            fuel = ?, coins = ?, repairs_needed = ?, current_node_id = ?,
            visited_nodes_json = ?, unlocked_skins_json = ?, equipped_skin_slug = ?,
            achievements_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (
            merged["level"],
            max(0, int(merged["xp"])),
            int(merged["completed_trajets"]),
            int(merged["successful_events"]),
            int(merged["distance_km"]),
            clamp(int(merged["fuel"]), 0, FUEL_CAPACITY_LITERS),
            max(0, int(merged["coins"])),
            max(0, int(merged["repairs_needed"])),
            merged["current_node_id"],
            json.dumps(merged["visited_nodes"]),
            json.dumps(merged["unlocked_skins"]),
            merged["equipped_skin_slug"],
            json.dumps(merged["achievements"]),
            user_id,
        ),
    )
    return get_progression(conn, user_id)


def apply_effect(conn, user_id, effect):
    current = serialize_progression(get_progression(conn, user_id))
    updates = {
        "xp": current["xp"] + int(effect.get("xp", 0)),
        "fuel": current["fuel"] + int(effect.get("fuel", 0)),
        "coins": 0,
        "repairs_needed": current["repairs_needed"] + int(effect.get("repairs_needed", 0)),
        "successful_events": current["successful_events"] + int(effect.get("successful_events", 0)),
    }
    updated = update_progression(conn, user_id, **updates)
    return sync_unlocks_and_achievements(conn, user_id, updated)


def _owned_skin_slugs(conn, user_id):
    return [
        row["slug"]
        for row in conn.execute(
            """
            SELECT DISTINCT skins.slug
            FROM inventory
            JOIN skins ON skins.id = inventory.item_id
            WHERE inventory.user_id = ?
              AND inventory.item_type = 'skin'
              AND inventory.status = 'unlocked'
            ORDER BY skins.id
            """,
            (user_id,),
        ).fetchall()
    ]


def _ensure_default_skin(conn, user_id):
    if _owned_skin_slugs(conn, user_id):
        return
    skin = conn.execute("SELECT id FROM skins WHERE slug = ?", (DEFAULT_SKIN_SLUG,)).fetchone()
    if skin:
        conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'skin', ?, 'unlocked')",
            (user_id, skin["id"]),
        )


def _grant_level_lootboxes(conn, user_id, level):
    for level_index in range(1, max(1, int(level)) + 1):
        existing = conn.execute(
            "SELECT 1 FROM inventory WHERE user_id = ? AND item_type = 'lootbox' AND item_id = ?",
            (user_id, level_index),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'lootbox', ?, 'active')",
                (user_id, level_index),
            )


def sync_unlocks_and_achievements(conn, user_id, progression_row=None):
    progression = serialize_progression(progression_row or get_progression(conn, user_id))
    _ensure_default_skin(conn, user_id)

    achievement_slugs = set(progression["achievements"])
    for achievement in conn.execute("SELECT * FROM achievements").fetchall():
        value = int(progression.get(achievement["condition_key"], 0))
        if value >= achievement["threshold"] and achievement["slug"] not in achievement_slugs:
            achievement_slugs.add(achievement["slug"])
            conn.execute(
                """
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                VALUES (?, ?)
                """,
                (user_id, achievement["id"]),
            )
            progression["xp"] += achievement["reward_xp"]

    updated = update_progression(
        conn,
        user_id,
        xp=progression["xp"],
        unlocked_skins=sorted(_owned_skin_slugs(conn, user_id)),
        achievements=sorted(achievement_slugs),
    )
    updated_progression = serialize_progression(updated)
    _grant_level_lootboxes(conn, user_id, updated_progression["level"])
    equipped = updated_progression["equipped_skin_slug"]
    owned = _owned_skin_slugs(conn, user_id)
    if owned and equipped not in owned:
        updated = update_progression(conn, user_id, equipped_skin_slug=DEFAULT_SKIN_SLUG if DEFAULT_SKIN_SLUG in owned else owned[0], unlocked_skins=sorted(owned))
    return updated
