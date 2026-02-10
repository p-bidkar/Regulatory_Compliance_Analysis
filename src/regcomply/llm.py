import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def get_client() -> OpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def default_model() -> str:
    return os.environ.get("OPENAI_MODEL", "meta/llama-3.1-8b-instruct")


def _clean_json(raw: str) -> str:
    cleaned = _THINK_RE.sub("", raw).strip()
    m = _JSON_BLOCK_RE.search(cleaned)
    if m:
        return m.group(1)
    m = _BARE_JSON_RE.search(cleaned)
    if m:
        return m.group(1)
    return cleaned


def chat_json(messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
    client = get_client()
    model = default_model()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    content = resp.choices[0].message.content or "{}"
    return _clean_json(content)


def chat_text(messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
    client = get_client()
    model = default_model()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    raw = resp.choices[0].message.content or ""
    return _THINK_RE.sub("", raw).strip()
