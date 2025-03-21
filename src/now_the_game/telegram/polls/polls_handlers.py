from pyrogram import Client, filters
from pyrogram.types import Message

from ... import logger
from .polls_service import polls_service


@Client.on_message(filters.poll)
async def on_poll(client: Client, message: Message):
    if not polls_service.is_poll(message):
        return

    poll = polls_service.get_poll(message)
    logger.info(f"Poll: {poll}")
