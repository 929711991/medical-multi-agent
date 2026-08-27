import re

from langchain.agents.middleware import ModelCallLimitMiddleware, PIIMiddleware, ToolCallLimitMiddleware

from app.core.config import get_settings


PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact_direct_identifiers(text: str) -> str:
    return EMAIL_PATTERN.sub("[REDACTED_EMAIL]", PHONE_PATTERN.sub("[REDACTED_PHONE]", text))


def build_agent_middleware() -> list[object]:
    settings = get_settings()
    return [
        PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True),
        PIIMiddleware(
            "phone",
            detector=PHONE_PATTERN.pattern,
            strategy="redact",
            apply_to_input=True,
            apply_to_output=True,
        ),
        ModelCallLimitMiddleware(run_limit=settings.model_call_limit, exit_behavior="error"),
        ToolCallLimitMiddleware(run_limit=settings.tool_call_limit, exit_behavior="error"),
    ]
