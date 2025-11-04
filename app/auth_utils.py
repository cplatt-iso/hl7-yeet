# --- START OF FILE app/auth_utils.py ---
"""Authentication helpers that support JWT and API key credentials."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, Optional

from flask import g, jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import current_user, get_jwt_identity, verify_jwt_in_request

from .extensions import bcrypt, db
from . import crud
from .models import ApiKey, User

API_KEY_HEADER = "X-API-Key"
API_KEY_AUTH_PREFIX = "apikey"
API_KEY_PREFIX_LENGTH = 8


def _extract_api_key() -> Optional[str]:
    header_value = request.headers.get(API_KEY_HEADER)
    if header_value:
        return header_value.strip()

    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        parts = auth_header.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == API_KEY_AUTH_PREFIX:
            return parts[1].strip()
    return None


def _set_auth_context(user: User, method: str, api_key: Optional[ApiKey] = None) -> None:
    g.auth_user = user
    g.auth_user_id = int(user.id)
    g.auth_via = method
    g.auth_api_key = api_key


def _clear_auth_context() -> None:
    g.auth_user = None
    g.auth_user_id = None
    g.auth_via = None
    g.auth_api_key = None


def validate_api_key(raw_key: str, *, update_last_used: bool = True) -> tuple[Optional[User], Optional[ApiKey]]:
    if not raw_key or len(raw_key) < API_KEY_PREFIX_LENGTH:
        return None, None

    key_prefix = raw_key[:API_KEY_PREFIX_LENGTH]
    db_key = crud.get_api_key_by_prefix(db, key_prefix)
    if not db_key or not db_key.is_active:
        return None, None

    if not bcrypt.check_password_hash(db_key.key_hash, raw_key):
        return None, None

    user = crud.get_user_by_id(db, db_key.user_id)
    if not user:
        return None, None

    if update_last_used:
        try:
            crud.update_api_key_last_used(db, key_prefix)
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.warning("Failed to update API key last_used: %s", exc)

    return user, db_key


def authenticate_request() -> Optional[ResponseReturnValue]:
    _clear_auth_context()

    raw_key = _extract_api_key()
    if raw_key:
        user, api_key = validate_api_key(raw_key)
        if not user:
            return jsonify({"error": "Invalid API key"}), 401
        _set_auth_context(user, "api_key", api_key)
        return None

    try:
        verify_jwt_in_request()
    except Exception:
        return jsonify({"error": "Missing or invalid credentials"}), 401

    user_obj = current_user
    if user_obj is None:
        identity = get_jwt_identity()
        if identity is None:
            return jsonify({"error": "Missing or invalid credentials"}), 401
        user_obj = crud.get_user_by_id(db, int(identity))
        if user_obj is None:
            return jsonify({"error": "Unknown user"}), 401

    _set_auth_context(user_obj, "jwt", None)
    return None


def auth_required(*, admin: bool = False) -> Callable[[Callable[..., ResponseReturnValue]], Callable[..., ResponseReturnValue]]:
    def decorator(fn: Callable[..., ResponseReturnValue]) -> Callable[..., ResponseReturnValue]:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            failure = authenticate_request()
            if failure is not None:
                return failure

            user = get_authenticated_user()
            if admin and not user.is_admin:
                logging.warning("User %s attempted admin route without privileges", user.username)
                return jsonify({"error": "Admins only."}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_authenticated_user() -> User:
    user = getattr(g, "auth_user", None)
    if user is not None:
        return user

    proxy_user = current_user
    if proxy_user is not None:
        return proxy_user  # type: ignore[return-value]

    identity = get_jwt_identity()
    if identity is None:
        raise RuntimeError("No authenticated user in context")
    db_user = crud.get_user_by_id(db, int(identity))
    if db_user is None:
        raise RuntimeError("User not found for active identity")
    _set_auth_context(db_user, "jwt")
    return db_user


def get_authenticated_user_id() -> int:
    user_id = getattr(g, "auth_user_id", None)
    if user_id is not None:
        return int(user_id)

    identity = get_jwt_identity()
    if identity is None:
        raise RuntimeError("No authenticated identity in context")
    try:
        value = int(identity)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise RuntimeError("Authenticated identity could not be coerced to int") from exc

    g.auth_user_id = value
    return value


def get_auth_method() -> Optional[str]:
    return getattr(g, "auth_via", None)


def get_active_api_key() -> Optional[ApiKey]:
    api_key = getattr(g, "auth_api_key", None)
    if api_key is not None:
        return api_key
    return None

# --- END OF FILE app/auth_utils.py ---
