from enum import Enum


# MODEL ROLE
class Roles(str, Enum):
    PENDING = "pending"
    USER = "user"
    ADMIN = "admin"
    VENDOR = "vendor"


# TOKEN_EXPIRY
SESSION_EXPIRY_TOKEN = 60 * 30
REFRESH_EXPIRY_TOKEN = 2 * 24 * 60 * 60


# ADMIN PERMISSION LEVEL
class PermissionLevel(str, Enum):
    LEVEL1 = "manager"
    LEVEL2 = "super_admin"


# REPORT
class ReportStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
