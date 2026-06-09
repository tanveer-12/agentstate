from __future__ import annotations

from typing import Any

runtime_trace: Any = None
RuntimeOTLPSpanExporter: Any = None
RuntimeTracerProvider: Any = None
RuntimeBatchSpanProcessor: Any = None

HAS_OTEL = False

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    runtime_trace = trace
    RuntimeOTLPSpanExporter = OTLPSpanExporter
    RuntimeTracerProvider = TracerProvider
    RuntimeBatchSpanProcessor = BatchSpanProcessor

    HAS_OTEL = True

except ImportError:
    pass


class _NoOpSpan:
    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: Exception) -> None:
        return None


class _NoOpTracer:
    def start_as_current_span(
        self,
        name: str,
        **kwargs: Any,
    ) -> _NoOpSpan:
        return _NoOpSpan()


_tracer: Any = None


def setup_tracing(
    service_name: str = "agentstatelib",
    exporter_endpoint: str = "http://localhost:4317",
) -> None:
    """
    Configure OpenTelemetry tracing.

    Call once before any graph.run() calls.

    Traces are exported to the configured endpoint
    (Jaeger locally, Datadog/Honeycomb/etc. in production).
    """
    global _tracer

    if not HAS_OTEL:
        raise ImportError(
            "OTel packages required. Install with: pip install agentstate-lib[otel]"
        )
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": service_name})
    provider = RuntimeTracerProvider(resource=resource)
    exporter = RuntimeOTLPSpanExporter(
        endpoint=exporter_endpoint,
        insecure=True,
    )
    processor = RuntimeBatchSpanProcessor(exporter)

    provider.add_span_processor(processor)
    runtime_trace.set_tracer_provider(provider)
    _tracer = runtime_trace.get_tracer(service_name)


def get_tracer() -> Any:
    """
    Get the configured tracer.

    Returns a no-op tracer if setup_tracing()
    has not been called.
    """
    return _tracer if _tracer is not None else _NoOpTracer()
