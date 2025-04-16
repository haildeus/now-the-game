import contextlib
import functools
import inspect
import json
import socket
import sys
import typing as tp

import opentelemetry
import pydantic
from opentelemetry.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import (Context, ReadableSpan,
                                            SimpleSpanProcessor, SpanExporter,
                                            SpanExportResult, SpanProcessor)
from opentelemetry.trace.status import StatusCode
from opentelemetry.util.types import AttributeValue

from src.shared import observability
from src.shared.config import shared_config
from src.shared.observability import schemas

__all__ = [
    "configure_tracing",
    "tracer",
    "traced_function",
    "async_traced_function",
]


_STATUS_CODE = {
    StatusCode.UNSET: "UNSET",
    StatusCode.OK: "OK",
    StatusCode.ERROR: "ERROR",
}


tracer: Tracer = opentelemetry.trace.get_tracer("deus-vult")


def _serialize_argument(value: tp.Any) -> AttributeValue:
    if isinstance(value, (str, bool, int, float)):
        return value

    if isinstance(value, (list, dict, tuple)):
        with contextlib.suppress(Exception):
            return json.dumps(value)

    if isinstance(value, pydantic.BaseModel):
        return value.model_dump_json()

    return str(value)


def traced_function(func):
    signature = inspect.signature(func)

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        with tracer.start_as_current_span(
            func.__name__,
            attributes={
                key: _serialize_argument(value)
                for key, value in bound.arguments.items()
            }
        ):
            return func(*args, **kwargs)

    return _wrapper


def async_traced_function(func):
    signature = inspect.signature(func)

    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        with tracer.start_as_current_span(
            func.__name__,
            attributes={
                key: _serialize_argument(value)
                for key, value in bound.arguments.items()
            }
        ):
            return await func(*args, **kwargs)

    return _wrapper


class ConsoleSpanProcessor(SpanProcessor):
    def __init__(self, out: tp.IO = sys.stdout) -> None:
        self.out = out

    def on_start(
        self,
        span: ReadableSpan,
        parent_context: Context | None = None
    ) -> None:
        self.out.write(f"[{span.context.trace_id}] open `{span.name}`\n")

    def on_end(self, span: ReadableSpan) -> None:
        if not span.context.trace_flags.sampled:
            return

        assert span.end_time is not None
        assert span.start_time is not None
        self.out.write(f"[{span.context.trace_id}] close `{span.name}` duration={span.end_time - span.start_time}\n")  # noqa: E501

    def shutdown(self) -> None:
        self.force_flush()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        self.out.flush()
        return True


class InserterExporter(SpanExporter):
    # round imports
    inserter: "observability.ch_utils.Inserter" = None  # type: ignore
    fqdn = socket.getfqdn()

    @staticmethod
    def _insure_attributes(attributes: tp.Mapping[str, tp.Any]) -> dict[str, str]:
        return {key: str(value) for key, value in attributes.items()}

    def export(self, spans: tp.Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            trace = schemas.Trace(
                timestamp=span.start_time,
                trace_id=hex(span.context.trace_id),
                span_id=hex(span.context.span_id),
                parent_span_id=hex(span.parent.span_id) if span.parent else "",
                trace_state=repr(span.context.trace_state),
                span_name=span.name,
                span_kind=str(span.kind),
                service_name=self.fqdn,
                resource_attributes=self._insure_attributes(span.resource.attributes),
                span_attributes=self._insure_attributes(span.attributes),
                duration=span.end_time - span.start_time,
                status_code=_STATUS_CODE[span.status.status_code],
                status_message=span.status.description or "",
                events_timestamps=[event.timestamp for event in span.events],
                events_names=[event.name for event in span.events],
                events_attributes=[
                    self._insure_attributes(event.attributes)
                    for event in span.events
                ],
                links_trace_ids=[hex(link.context.trace_id) for link in span.links],
                links_span_ids=[hex(link.context.span_id) for link in span.links],
                links_trace_states=[
                    repr(link.context.trace_state)
                    for link in span.links
                ],
                links_attributes=[
                    self._insure_attributes(link.attributes)
                    for link in span.links
                ],
                app_env=shared_config.app_env,
                stage=shared_config.stage,
            )

            self.inserter.insert(trace)

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        # All shutdown and force_flush operations will be handled on the Inserter side on exit.
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracing(inserter_class: tp.Type["observability.ch_utils.Inserter"]):
    InserterExporter.inserter = inserter_class("operation.traces")
    provider = TracerProvider()

    provider.add_span_processor(SimpleSpanProcessor(InserterExporter()))
    opentelemetry.trace.set_tracer_provider(provider)
