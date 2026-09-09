"""Bounded, synchronous adapters run in FastAPI's worker thread pool."""

from typing import Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


class ProviderError(Exception):
    """Only application-owned error codes may cross the adapter boundary."""


class Generation(BaseModel):
    output: str = Field(max_length=200000)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AIProvider(Protocol):
    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> Generation: ...
    def health_check(self) -> bool: ...


class Message(BaseModel):
    content: str


class Choice(BaseModel):
    message: Message


class Usage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class Completion(BaseModel):
    choices: list[Choice] = Field(min_length=1)
    usage: Usage | None = None


class OpenAICompatibleProvider:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.transport = transport

    def _client(self) -> httpx.Client:
        if not settings.AI_BASE_URL or not settings.AI_API_KEY:
            raise ProviderError("provider_not_configured")
        return httpx.Client(
            base_url=settings.AI_BASE_URL.rstrip("/") + "/",
            headers={
                "Authorization": f"Bearer {settings.AI_API_KEY.get_secret_value()}"
            },
            timeout=httpx.Timeout(settings.AI_TIMEOUT_SECONDS, connect=5),
            follow_redirects=False,
            transport=self.transport,
        )

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> Generation:
        try:
            with (
                self._client() as client,
                client.stream(
                    "POST",
                    "chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_output_tokens,
                        "stream": False,
                    },
                ) as response,
            ):
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1000000:
                        raise ProviderError("provider_response_too_large")
                result = Completion.model_validate_json(body)
                usage = result.usage or Usage()
                return Generation(
                    output=result.choices[0].message.content, **usage.model_dump()
                )
        except httpx.TimeoutException:
            raise ProviderError("provider_timeout") from None
        except httpx.HTTPError:
            raise ProviderError("provider_unavailable") from None
        except ValidationError:
            raise ProviderError("provider_invalid_response") from None

    def health_check(self) -> bool:
        try:
            with self._client() as client:
                return client.get("models").is_success
        except ProviderError, httpx.HTTPError:
            return False


def get_provider() -> AIProvider:
    return OpenAICompatibleProvider()
