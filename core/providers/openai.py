import requests
from typing import Any
from core.providers.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        base_api_url: str | None = None,
        api_key: str = "NO_API_KEY",
    ):
        self.base_url = base_url.rstrip("/")
        self.base_api_url = base_api_url.rstrip("/") if base_api_url else None
        self.api_key = api_key

    @property
    def name(self) -> str:
        """Retorna o nome do provedor."""
        return "OpenAI compatible"

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        api_kwargs = {
            "model": model,
            "messages": messages,
        }
        if tools:
            api_kwargs["tools"] = tools

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        r = requests.post(url, headers=headers, json=api_kwargs, timeout=300)
        r.raise_for_status()
        return r.json()

    def unload_model(self, model: str) -> dict[str, Any]:
        if not self.base_api_url:
            raise ValueError("Base API URL is not set.")
        url = f"{self.base_api_url}/models/unload"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {"instance_id": model}
        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()
