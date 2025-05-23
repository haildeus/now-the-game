import logging

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.handlers.chat_member_updated_handler import ChatMemberUpdatedHandler
from pyrogram.handlers.handler import Handler
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup

from src.now_the_game.telegram.text.art import JOIN_THE_CRUSADE_MESSAGE
from src.now_the_game.telegram.text.buttons import LAUNCH_GAME_BUTTON

logger = logging.getLogger("deus-vult.telegram.memberships")


class ChatMembershipHandlers:
    """
    Chat membership handlers class
    """

    @staticmethod
    async def is_new_chat_member(
        _, __: Client, chat_member_updated: ChatMemberUpdated
    ) -> bool:
        if chat_member_updated.new_chat_member:
            return True
        return False

    @staticmethod
    async def is_bot_membership_update(
        _, __: Client, chat_member_updated: ChatMemberUpdated
    ) -> bool:
        if chat_member_updated.new_chat_member:
            check_object = chat_member_updated.new_chat_member
        else:
            check_object = chat_member_updated.old_chat_member

        if check_object.user.is_self:
            return True

        return False

    @staticmethod
    async def bot_join_new_chat(
        client: Client,
        chat_member_updated: ChatMemberUpdated,
    ) -> None:
        """
        Process a new chat membership event and add it to the database.
        """

        await client.send_message(
            chat_member_updated.chat.id,
            JOIN_THE_CRUSADE_MESSAGE,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            LAUNCH_GAME_BUTTON, callback_data="launch_game"
                        ),
                    ]
                ]
            ),
        )

    @property
    def chat_membership_handlers(self) -> list[Handler]:
        bot_membership_filter = filters.create(self.is_bot_membership_update)  # type: ignore
        new_chat_member_filter = filters.create(self.is_new_chat_member)  # type: ignore
        return [
            # We do it to catch the case when the bot joins the chat
            # (avoid updates on block notifications)
            ChatMemberUpdatedHandler(
                ChatMembershipHandlers.bot_join_new_chat,
                bot_membership_filter & new_chat_member_filter,
            ),
        ]
