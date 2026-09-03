import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.core.security import hash_pwd
from backend.models.users import Users
from backend.schemas.auth import UserIn


class AuthService:
    async def get_user_by_id(
        self, id: uuid.UUID, session: AsyncSession
    ) -> Users | None:
        statement = (
            select(Users)
            .where(Users.id == id)
            .options(
                joinedload(Users.user_profile),
                joinedload(Users.vendor_profile),
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self, email: str, session: AsyncSession
    ) -> Users | None:
        statement = (
            select(Users)
            .where(Users.email == email)
            .options(joinedload(Users.user_profile), joinedload(Users.vendor_profile))
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create_user(self, user_data: UserIn, session: AsyncSession) -> Users:
        user_dict = user_data.model_dump()
        user_dict["password"] = hash_pwd(user_data.password)
        new_user = Users(**user_dict)

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        return new_user

    async def update_user(
        self, id: uuid.UUID, data: dict, session: AsyncSession
    ) -> Users | None:
        user = await self.get_user_by_id(id, session)

        if not user:
            return None  # <-- ADD THIS LINE

        for field, value in data.items():
            if hasattr(user, field) and field != "id":
                setattr(user, field, value)

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user

    async def delete_user(self, id: uuid.UUID, session: AsyncSession) -> bool:
        user = await self.get_user_by_id(id, session)

        if not user:
            return False  # <-- guard clause: never try to delete None

        await session.delete(user)
        await session.commit()

        return True
