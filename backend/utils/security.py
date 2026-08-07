from passlib.context import CryptContext
from passlib.exc import MalformedHashError, UnknownHashError

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_pwd(password: str) -> str:
    return pwd_context.hash(password)


def verify_pwd(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except (UnknownHashError, MalformedHashError):
        return False
