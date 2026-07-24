"""
Verifies Telegram WebApp `initData` so the backend can trust who's calling it.
Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Without this, anyone could POST a fake telegram_id to your API and drain
other people's balances -- this check is not optional for a money app.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400):
    """
    Returns the parsed user dict if init_data is valid and fresh, else None.
    """
    if not init_data:
        return None

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(pairs.get("auth_date", 0))
    if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
        return None

    user_json = pairs.get("user")
    if not user_json:
        return None

    try:
        user = json.loads(user_json)
    except json.JSONDecodeError:
        return None

    user["_start_param"] = pairs.get("start_param")
    return user
