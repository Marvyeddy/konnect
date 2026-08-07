from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.users import Users
from backend.schemas.auth import AuthIn
from backend.utils.security import hash_pwd


class AuthServices:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(Users).where(Users.email == email)
        result = await session.exec(statement)

        return result.first()

    async def get_user_by_id(self, id: str, session: AsyncSession):
        statement = select(Users).where(Users.id == id)
        result = await session.exec(statement)

        return result.first()

    async def create_user(self, user_data: AuthIn, session: AsyncSession):
        user_dict = user_data.model_dump()
        user_dict["password"] = hash_pwd(user_data.password)

        new_user = Users(**user_dict)

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        return new_user
