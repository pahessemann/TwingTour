import json
import random

from backend.models.errors import ApiError
from backend.services.progression_service import get_progression, serialize_progression, update_progression


DEFAULT_SKIN_SLUG = "twingo-bleu-mediterranee"
RARITY_ORDER = ["Commun", "Peu commun", "Rare", "Epique", "Legendaire", "Mythique"]
LOOTBOX_WEIGHTS = {
    "Commun": 52,
    "Peu commun": 27,
    "Rare": 13,
    "Epique": 6,
    "Legendaire": 1.7,
    "Mythique": 0.3,
}


def _skin_row_to_dict(row):
    skin = dict(row)
    skin["palette"] = json.loads(skin.pop("palette_json") or "[]")
    return skin


def _owned_counts(conn, user_id):
    rows = conn.execute(
        """
        SELECT skins.slug, COUNT(*) AS owned_count
        FROM inventory
        JOIN skins ON skins.id = inventory.item_id
        WHERE inventory.user_id = ?
          AND inventory.item_type = 'skin'
          AND inventory.status = 'unlocked'
        GROUP BY skins.slug
        """,
        (user_id,),
    ).fetchall()
    return {row["slug"]: row["owned_count"] for row in rows}


def _owned_slugs(conn, user_id):
    return sorted(slug for slug, count in _owned_counts(conn, user_id).items() if count > 0)


def _sync_progression_skins(conn, user_id):
    progress = serialize_progression(get_progression(conn, user_id))
    owned = _owned_slugs(conn, user_id)
    if not owned:
        default = conn.execute("SELECT id FROM skins WHERE slug = ?", (DEFAULT_SKIN_SLUG,)).fetchone()
        if default:
            conn.execute(
                "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'skin', ?, 'unlocked')",
                (user_id, default["id"]),
            )
            owned = _owned_slugs(conn, user_id)
    equipped = progress["equipped_skin_slug"] if progress["equipped_skin_slug"] in owned else (DEFAULT_SKIN_SLUG if DEFAULT_SKIN_SLUG in owned else owned[0])
    return update_progression(conn, user_id, unlocked_skins=owned, equipped_skin_slug=equipped)


def lootbox_count(conn, user_id):
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM inventory
        WHERE user_id = ? AND item_type = 'lootbox' AND status = 'active'
        """,
        (user_id,),
    ).fetchone()
    return int(row["count"])


def list_skins(conn, user_id):
    progress = serialize_progression(_sync_progression_skins(conn, user_id))
    counts = _owned_counts(conn, user_id)
    skins = []
    for row in conn.execute(
        """
        SELECT *
        FROM skins
        ORDER BY min_level, id
        """
    ).fetchall():
        skin = _skin_row_to_dict(row)
        owned_count = int(counts.get(skin["slug"], 0))
        rarity_index = RARITY_ORDER.index(skin["rarity"]) if skin["rarity"] in RARITY_ORDER else 0
        skin["owned_count"] = owned_count
        skin["duplicate_count"] = max(0, owned_count - 1)
        skin["unlocked"] = owned_count > 0
        skin["equipped"] = skin["slug"] == progress["equipped_skin_slug"]
        skin["can_fuse"] = owned_count >= 5 and rarity_index < len(RARITY_ORDER) - 1
        skins.append(skin)
    return skins


def equip_skin(conn, user_id, slug):
    counts = _owned_counts(conn, user_id)
    if counts.get(slug, 0) <= 0:
        raise ApiError(403, "Skin non debloque.")
    skin = conn.execute("SELECT * FROM skins WHERE slug = ?", (slug,)).fetchone()
    if not skin:
        raise ApiError(404, "Skin introuvable.")
    progress_row = update_progression(conn, user_id, equipped_skin_slug=slug, unlocked_skins=_owned_slugs(conn, user_id))
    return {
        "skin": slug,
        "progression": serialize_progression(progress_row),
        "skins": list_skins(conn, user_id),
        "lootboxes": lootbox_count(conn, user_id),
    }


def _weighted_rarity():
    total = sum(LOOTBOX_WEIGHTS.values())
    pick = random.random() * total
    cursor = 0
    for rarity in RARITY_ORDER:
        cursor += LOOTBOX_WEIGHTS.get(rarity, 0)
        if pick <= cursor:
            return rarity
    return "Commun"


def _random_skin_by_rarity(conn, rarity):
    rows = conn.execute("SELECT * FROM skins WHERE rarity = ? ORDER BY RANDOM()", (rarity,)).fetchall()
    if not rows:
        rows = conn.execute("SELECT * FROM skins ORDER BY RANDOM()").fetchall()
    if not rows:
        raise ApiError(500, "Aucun skin disponible.")
    return rows[0]


def _grant_skin(conn, user_id, skin_id):
    conn.execute(
        "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'skin', ?, 'unlocked')",
        (user_id, skin_id),
    )
    return _sync_progression_skins(conn, user_id)


def open_lootbox(conn, user_id):
    lootbox = conn.execute(
        """
        SELECT id
        FROM inventory
        WHERE user_id = ? AND item_type = 'lootbox' AND status = 'active'
        ORDER BY item_id, id
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if not lootbox:
        raise ApiError(400, "Aucune lootbox disponible.")
    rarity = _weighted_rarity()
    skin = _random_skin_by_rarity(conn, rarity)
    conn.execute("UPDATE inventory SET status = 'opened' WHERE id = ?", (lootbox["id"],))
    progress = _grant_skin(conn, user_id, skin["id"])
    return {
        "skin": _skin_row_to_dict(skin),
        "rarity": rarity,
        "progression": serialize_progression(progress),
        "skins": list_skins(conn, user_id),
        "lootboxes": lootbox_count(conn, user_id),
    }


def fuse_skin(conn, user_id, slug):
    source = conn.execute("SELECT * FROM skins WHERE slug = ?", (slug,)).fetchone()
    if not source:
        raise ApiError(404, "Skin introuvable.")
    source = _skin_row_to_dict(source)
    try:
        rarity_index = RARITY_ORDER.index(source["rarity"])
    except ValueError as exc:
        raise ApiError(400, "Rareté inconnue pour ce skin.") from exc
    if rarity_index >= len(RARITY_ORDER) - 1:
        raise ApiError(400, "Ce skin est deja au tier maximum.")
    copies = conn.execute(
        """
        SELECT inventory.id
        FROM inventory
        JOIN skins ON skins.id = inventory.item_id
        WHERE inventory.user_id = ?
          AND inventory.item_type = 'skin'
          AND inventory.status = 'unlocked'
          AND skins.slug = ?
        ORDER BY inventory.id
        LIMIT 5
        """,
        (user_id, slug),
    ).fetchall()
    if len(copies) < 5:
        raise ApiError(400, "Il faut 5 copies du meme skin pour fusionner.")
    consumed_ids = [row["id"] for row in copies]
    placeholders = ",".join("?" for _ in consumed_ids)
    conn.execute(f"UPDATE inventory SET status = 'fused' WHERE id IN ({placeholders})", consumed_ids)
    target = _random_skin_by_rarity(conn, RARITY_ORDER[rarity_index + 1])
    progress = _grant_skin(conn, user_id, target["id"])
    return {
        "consumed": source,
        "skin": _skin_row_to_dict(target),
        "progression": serialize_progression(progress),
        "skins": list_skins(conn, user_id),
        "lootboxes": lootbox_count(conn, user_id),
    }
