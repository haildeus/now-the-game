import logging
from datetime import datetime
from typing import cast

from pyrogram.client import Client
from pyrogram.types import Message, Poll

from src.now_the_game.telegram.polls.polls_model import poll_model, poll_option_model
from src.now_the_game.telegram.polls.polls_schemas import (
    PollOptionTable,
    PollTable,
    SendPollEventPayload,
)
from src.shared.base import BaseService
from src.shared.event_bus import EventBus
from src.shared.event_registry import PollTopics
from src.shared.events import Event
from src.shared.observability.traces import async_traced_function
from src.shared.uow import current_uow

logger = logging.getLogger("deus-vult.telegram.polls")


class PollsService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.poll_model = poll_model
        self.poll_option_model = poll_option_model

    @EventBus.subscribe(PollTopics.POLL_SEND)
    @async_traced_function
    async def on_send_poll(
        self,
        event: Event,
        client: Client,
    ) -> None:
        payload = cast(
            SendPollEventPayload,
            event.extract_payload(event, SendPollEventPayload),
        )
        save_to_db = payload.save

        logger.debug("Sending poll to %s", payload.chat_id)
        poll_message = await client.send_poll(
            chat_id=payload.chat_id,
            question=payload.question,
            options=payload.options,
            is_anonymous=payload.is_anonymous,
            explanation=payload.explanation,
        )
        logger.debug("Poll sent to %s", payload.chat_id)

        active_uow = current_uow.get()

        if save_to_db and active_uow:
            logger.debug("Converting poll to database model")
            db = await active_uow.get_session()
            poll_from_pyrogram = await PollTable.from_pyrogram(poll_message)
            poll_options_from_pyrogram = await PollOptionTable.from_pyrogram(
                poll_id=poll_from_pyrogram.object_id, options=poll_message.poll.options
            )

            logger.debug("Adding poll to database")
            await self.poll_model.add(db, poll_from_pyrogram)
            await self.poll_option_model.add(db, poll_options_from_pyrogram)
            await db.flush()

    async def is_poll(self, message: Message) -> bool:
        try:
            assert message.poll
            return True
        except AssertionError:
            return False

    async def get_poll(self, message: Message) -> Poll:
        if not await self.is_poll(message):
            raise ValueError("Message is not a poll")
        return message.poll

    @async_traced_function
    async def send_poll(
        self,
        client: Client,
        chat_id: int | str,
        question: str,
        options: list[str],
        schedule: datetime | None = None,
    ) -> Message:
        poll_message = await client.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            schedule_date=schedule,
        )
        return poll_message

    @async_traced_function
    async def stop_poll(
        self,
        client: Client,
        chat_id: int | str,
        message_id: int,
    ) -> Poll:
        stopped_poll = await client.stop_poll(
            chat_id=chat_id,
            message_id=message_id,
        )
        return stopped_poll
