import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from backend.models.errors import ApiError
from backend.services.progression_service import serialize_progression, sync_unlocks_and_achievements


TOKEN_SECRET = os.environ.get("EUROTWINGO_SECRET", "eurotwingo-dev-secret-change-me")
TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_SKIN_SLUG = "twingo-bleu-mediterranee"


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
    return hmac.compare_digest(digest, expected)


def create_token(user):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["display_name"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    signing_input = ".".join([
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
        _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
    ])
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def decode_token(token):
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ApiError(401, "Token invalide.") from exc
    signing_input = f"{header_b64}.{payload_b64}"
    expected = hmac.new(TOKEN_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    actual = _b64decode(signature_b64)
    if not hmac.compare_digest(expected, actual):
        raise ApiError(401, "Signature invalide.")
    payload = json.loads(_b64decode(payload_b64))
    if payload.get("exp", 0) < int(time.time()):
        raise ApiError(401, "Session expiree.")
    return payload


def get_user_by_id(conn, user_id):
    return conn.execute("SELECT id, email, display_name, created_at, last_login_at FROM users WHERE id = ?", (user_id,)).fetchone()


def register(conn, email, password, display_name=None):
    email = (email or "").strip().lower()
    display_name = (display_name or email.split("@")[0] or "Pilote").strip()
    if "@" not in email or "." not in email:
        raise ApiError(400, "Email invalide.")
    if len(password or "") < 6:
        raise ApiError(400, "Le mot de passe doit contenir au moins 6 caracteres.")
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise ApiError(409, "Un compte existe deja avec cet email.")

    cursor = conn.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        (email, hash_password(password), display_name),
    )
    user_id = cursor.lastrowid
    conn.execute(
        """
        INSERT INTO progression (user_id, current_node_id, visited_nodes_json, unlocked_skins_json, equipped_skin_slug)
        VALUES (?, 'PAR', '["PAR"]', ?, ?)
        """,
        (user_id, json.dumps([DEFAULT_SKIN_SLUG]), DEFAULT_SKIN_SLUG),
    )
    skin = conn.execute("SELECT id FROM skins WHERE slug = ?", (DEFAULT_SKIN_SLUG,)).fetchone()
    if skin:
        conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'skin', ?, 'unlocked')",
            (user_id, skin["id"]),
        )

    user = get_user_by_id(conn, user_id)
    progression = sync_unlocks_and_achievements(conn, user_id)
    return {
        "token": create_token(user),
        "user": dict(user),
        "progression": serialize_progression(progression),
    }


def login(conn, email, password):
    email = (email or "").strip().lower()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not verify_password(password or "", user["password_hash"]):
        raise ApiError(401, "Email ou mot de passe incorrect.")
    conn.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    public_user = get_user_by_id(conn, user["id"])
    progression = sync_unlocks_and_achievements(conn, user["id"])
    return {
        "token": create_token(public_user),
        "user": dict(public_user),
        "progression": serialize_progression(progression),
    }
