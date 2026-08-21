from enum import Enum


# MODEL ROLE
class Roles(str, Enum):
    USER = "user"
    ADMIN = "admin"
    VENDOR = "vendor"


# TOKEN_EXPIRY
SESSION_EXPIRY_TOKEN = 60 * 30
REFRESH_EXPIRY_TOKEN = 2 * 24 * 60 * 60
