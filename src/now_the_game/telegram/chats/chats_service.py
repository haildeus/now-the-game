from pyrogram.client import Client
from pyrogram.types import Chat, ChatMember

from src import BaseService, Event, event_bus
from src.now_the_game import logger
from src.now_the_game.telegram.chats.chats_model import chat_model
from src.now_the_game.telegram.chats.chats_schemas import (
    AddChatEventPayload,
    ChatTable,
    ChatTopics,
)


class ChatsService(BaseService):
    def __init__(self, client: Client):
        super().__init__()
        self.client = client
        self.model = chat_model

    @event_bus.subscribe(ChatTopics.CHAT_ADDED.value)
    async def on_add_chat(self, event: Event) -> None:
        if not isinstance(event.payload, AddChatEventPayload):
            payload = AddChatEventPayload(**event.payload)  # type: ignore
        else:
            payload = event.payload

        chat_core_info = await ChatTable.from_pyrogram(payload.message)
        db = payload.db_session
        logger.debug(f"Adding chat: {chat_core_info}")
        await self.model.add(db, chat_core_info)

    async def get(
        self,
        chat_id: int | str,
    ) -> Chat:
        chat_request = await self.client.get_chat(
            chat_id=chat_id,
        )
        return chat_request

    async def download_chat_photo(
        self,
        chat_id: int | str,
    ) -> bytes:
        chat = await self.get(chat_id)
        photo_small = chat.photo.small_file_id
        bytes_io_object = await self.client.download_media(  # type: ignore
            message=photo_small,
            in_memory=True,
        )
        bytes_object = bytes_io_object.getvalue()  # type: ignore
        if bytes_object is None:
            raise ValueError("Bytes object is None")

        return bytes_object  # type: ignore

    async def get_member(
        self,
        chat_id: int | str,
        user_id: int | str,
    ) -> ChatMember:
        chat_member_request = await self.client.get_chat_member(
            chat_id=chat_id,
            user_id=user_id,
        )
        return chat_member_request

    async def get_members_count(
        self,
        chat_id: int | str,
    ) -> int:
        chat_members_count_request = await self.client.get_chat_members_count(
            chat_id=chat_id,
        )
        return chat_members_count_request

    async def get_photos_count(
        self,
        chat_id: int | str,
    ) -> int:
        chat_photos_count_request = await self.client.get_chat_photos_count(
            chat_id=chat_id,
        )
        return chat_photos_count_request
