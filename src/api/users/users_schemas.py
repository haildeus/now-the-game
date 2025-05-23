"""
User-specific schema definitions.
This module re-exports the User-related schemas from the central schema module.
"""

from typing import TYPE_CHECKING, Any

from pyrogram.types import Message, User
from sqlmodel import Field, Relationship

from src.api.inventory.inventory_schemas import InventoryPublic, InventoryTable
from src.shared.base import BaseSchema
from src.shared.events import EventPayload

if TYPE_CHECKING:
    from src.now_the_game.telegram.memberships.memberships_schemas import (
        ChatMembershipTable,
    )
    from src.now_the_game.telegram.messages.messages_schemas import MessageTable


class AddUserPayload(EventPayload):
    user: User


class NewUserPayload(EventPayload):
    user: "UserBase"


class UserBase(BaseSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    username: str | None = Field(default=None, min_length=1, max_length=100)
    is_premium: bool = Field(default=False)
    bio: str | None = Field(default=None, min_length=1, max_length=255)
    photo_url: str | None = Field(default=None, min_length=1, max_length=255)


class UserPublic(UserBase):
    inventory: InventoryPublic | None = Field(default=None)


class UserTable(UserBase, table=True):
    __tablename__ = "users"  # type: ignore

    inventory: InventoryTable = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )

    chats_member: list["ChatMembershipTable"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    messages: list["MessageTable"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # --- End Relationships ---

    @classmethod
    async def from_fields(cls, **kwargs: Any) -> "UserTable":
        """Create a user from a dictionary of fields"""
        try:
            assert "object_id" in kwargs
            assert "first_name" in kwargs
            assert "is_premium" in kwargs
        except AssertionError as e:
            raise ValueError("Missing required fields") from e

        return cls(
            object_id=kwargs.get("object_id", 0),
            first_name=kwargs.get("first_name", ""),
            last_name=kwargs.get("last_name", None),
            username=kwargs.get("username", None),
            is_premium=kwargs.get("is_premium", False),
            bio=kwargs.get("bio", None),
            photo_url=kwargs.get("photo_url", None),
        )

    @classmethod
    async def from_user(cls, user: User) -> "UserTable":
        return cls(
            object_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            is_premium=user.is_premium,
        )

    @classmethod
    async def from_pyrogram(cls, message: Message) -> "UserTable":
        """Create a user from a pyrogram message"""

        return cls(
            object_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
            is_premium=message.from_user.is_premium,
        )
