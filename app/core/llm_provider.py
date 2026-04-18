from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        ...

    @abstractmethod
    async def stream_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        ...


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    @async_retry()
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    async def stream_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


class GroqProvider(OpenAIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = settings.groq_model


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)

        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model
        )

    @async_retry()
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        prompt = f"{system_prompt}\n\n{user_prompt}"

        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
        )

        return response.text or ""

    async def stream_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        prompt = f"{system_prompt}\n\n{user_prompt}"

        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
                await asyncio.sleep(0)


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseLLMProvider:
    providers = {
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "gemini": GeminiProvider,
    }

    provider = providers.get(settings.llm_provider)

    if not provider:
        raise ValueError("Invalid LLM provider")

    logger.info(
        "LLM provider loaded",
        provider=settings.llm_provider,
        model=settings.active_model,
    )

    return provider()