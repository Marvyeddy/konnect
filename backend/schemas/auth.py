from pydantic import BaseModel, EmailStr


class UserIn(BaseModel):
    username: str
    email: EmailStr
    password: str
