from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadTimeSignature
from jwt.exceptions import InvalidSignatureError

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN

from .config import config as cfg
from .logging import get_app_logger

logger = get_app_logger(__name__)


# ------------------------
# TOKEN CREATION
# ------------------------
def create_token(data: dict, token_type: str, expiry: int):
    data_copy = data.copy()

    expiry_period = datetime.now(UTC) + timedelta(seconds=expiry)

    data_copy.update({"type": token_type, "exp": expiry_period})

    return jwt.encode(payload=data_copy, key=cfg.JWT_KEY, algorithm=cfg.JWT_ALG)


def create_session_token(data: dict):
    return create_token(data=data, token_type="session", expiry=SESSION_EXPIRY_TOKEN)


def create_refresh_token(data: dict):
    return create_token(data=data, token_type="refresh", expiry=REFRESH_EXPIRY_TOKEN)


def decode_token(token: str) -> dict[str, Any]:
    try:
        token_data = jwt.decode(jwt=token, key=cfg.JWT_KEY, algorithms=[cfg.JWT_ALG])
        return token_data
    except InvalidSignatureError as e:
        logger.error("Invalid signature decoding token: %s", str(e))
        return None
    except jwt.ExpiredSignatureError as e:
        logger.error("Token has expired: %s", str(e))
        return None
    except jwt.DecodeError as e:
        logger.error("Failed to decode token: %s", str(e))
        return None


# ----------------------
#  PASSWORD HASHING
# ----------------------
ph = PasswordHasher()


def hash_pwd(password: str):
    return ph.hash(password)


def verify_pwd(password: str, hash: str) -> bool:
    try:
        return ph.verify(hash, password)
    except VerifyMismatchError as e:
        logger.error("Password verification failed: %s", str(e))
        return False


# ----------------------------------
# TOKENIZATION OF CREDENTIALS
# ----------------------------------
serializer = URLSafeTimedSerializer(secret_key=cfg.JWT_KEY, salt="serialized_token")


def create_url_safe_token(data: dict):
    token = serializer.dumps(data)
    return token


def decode_url_safe_token(token: str) -> dict:
    try:
        token_data = serializer.loads(token)

        return token_data

    except BadTimeSignature as e:
        logger.error("Failed to decode url safe token: %s", str(e))
        return None
