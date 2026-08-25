from pydantic import BaseModel, EmailStr


class UserIn(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class ResetIn(BaseModel):
    new_password: str
    confirm_password: str
