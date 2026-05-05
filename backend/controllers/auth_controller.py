from backend.models.errors import ApiError
from backend.services import auth_service
from backend.services.card_service import get_user_inventory
from backend.services.progression_service import serialize_progression, sync_unlocks_and_achievements
from backend.services.skin_service import list_skins, lootbox_count


def require_user(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "Authentification requise.")
    payload = auth_service.decode_token(header.removeprefix("Bearer ").strip())
    user = auth_service.get_user_by_id(request.conn, payload["sub"])
    if not user:
        raise ApiError(401, "Utilisateur introuvable.")
    return user


def register(request):
    data = request.json
    return auth_service.register(
        request.conn,
        data.get("email"),
        data.get("password"),
        data.get("display_name"),
    )


def login(request):
    data = request.json
    return auth_service.login(request.conn, data.get("email"), data.get("password"))


def me(request):
    user = require_user(request)
    progression = sync_unlocks_and_achievements(request.conn, user["id"])
    return {
        "user": dict(user),
        "progression": serialize_progression(progression),
        "skins": list_skins(request.conn, user["id"]),
        "lootboxes": lootbox_count(request.conn, user["id"]),
        "inventory": get_user_inventory(request.conn, user["id"]),
    }
