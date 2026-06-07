import logging
import os
import litellm
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Global variables to hold providers so we can shut them down later
_tracer_provider = None
_logger_provider = None


def setup_telemetry():
    """Initialize OpenTelemetry providers and Litellm callback."""
    global _tracer_provider, _logger_provider

    from config import ensure_env

    otel_endpoint = ensure_env("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource(attributes={"service.name": "operations-assistant-crew"})

    # Trace configuration
    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint, insecure=True))
    )

    # Bypass restriction and set the tracer provider globally
    trace._TRACER_PROVIDER = None
    trace.set_tracer_provider(_tracer_provider)

    # Log configuration
    _logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=otel_endpoint, insecure=True)
    _logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(_logger_provider)

    # Attach OTLP Logging Handler to standard Python logging root logger
    handler = LoggingHandler(level=logging.INFO, logger_provider=_logger_provider)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    # Register the custom Litellm callback
    _register_litellm_callback()


# Global dictionary to map OTel contexts across background threads
active_otel_contexts = {}


def custom_input_callback(kwargs, *args, **kwargs_rest):
    # This runs synchronously BEFORE the LLM call, so OTel context is still valid
    call_id = kwargs.get("litellm_call_id")
    if call_id:
        from opentelemetry import context as otel_context

        active_otel_contexts[call_id] = otel_context.get_current()


def custom_success_callback(kwargs, response_obj, start_time, end_time):
    # This runs in a background thread, so we must manually attach the context
    call_id = kwargs.get("litellm_call_id")
    ctx = active_otel_contexts.pop(call_id, None) if call_id else None

    from opentelemetry import context as otel_context

    token = otel_context.attach(ctx) if ctx else None

    try:
        model = kwargs.get("model", "unknown_model")
        messages = kwargs.get("messages", [])
        tracer = trace.get_tracer("litellm")

        with tracer.start_as_current_span(f"litellm.completion: {model}") as span:
            span.set_attribute("gen_ai.prompt", str(messages))
            if (
                response_obj
                and hasattr(response_obj, "choices")
                and len(response_obj.choices) > 0
            ):
                content = response_obj.choices[0].message.content
                span.set_attribute("gen_ai.completion", str(content))
    finally:
        if token:
            otel_context.detach(token)


def custom_failure_callback(kwargs, response_obj, start_time, end_time):
    # This runs in a background thread, so we must manually attach the context
    call_id = kwargs.get("litellm_call_id")
    ctx = active_otel_contexts.pop(call_id, None) if call_id else None

    from opentelemetry import context as otel_context

    token = otel_context.attach(ctx) if ctx else None

    try:
        model = kwargs.get("model", "unknown_model")
        exception = kwargs.get("exception", "Unknown error")
        tracer = trace.get_tracer("litellm")

        with tracer.start_as_current_span(
            f"litellm.completion (failed): {model}"
        ) as span:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(exception))
    finally:
        if token:
            otel_context.detach(token)


def _register_litellm_callback():
    litellm.input_callback = [custom_input_callback]
    # Add "langfuse" to seamlessly integrate it alongside our custom OTel Aspire callbacks
    litellm.success_callback = [custom_success_callback, "langfuse"]
    litellm.failure_callback = [custom_failure_callback, "langfuse"]


def shutdown_telemetry():
    """Flush and shutdown OpenTelemetry providers."""
    if _tracer_provider:
        _tracer_provider.force_flush()
        _tracer_provider.shutdown()
    if _logger_provider:
        _logger_provider.force_flush()
        _logger_provider.shutdown()

    try:
        from langfuse.decorators import langfuse_context

        langfuse_context.flush()
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to flush Langfuse: {e}")

    # Give LiteLLM's isolated Langfuse background thread time to flush over the network
    # before the python process exits and kills all daemon threads.
    import time

    time.sleep(2)
