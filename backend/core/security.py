from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN

from .config import config as cfg
from .logging import get_app_logger

logger = get_app_logger(__name__)


# ------------------------
# TOKEN CREATION
# ------------------------
def create_token(data: dict, token_type: str, expiry: int):
    data_copy = data.copy()

    expiry_period = datetime.now(tz=True) + timedelta(seconds=expiry)

    data_copy.update({"type": token_type, "exp": expiry_period})

    return jwt.encode(payload=data_copy, key=cfg.JWT_KEY, algorithm=cfg.JWT_ALG)


def create_session_token(data: dict):
    return create_token(data=data, token_type="session", expiry=SESSION_EXPIRY_TOKEN)


def create_refresh_token(data: dict):
    return create_token(data=data, token_type="refresh", expiry=REFRESH_EXPIRY_TOKEN)


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
