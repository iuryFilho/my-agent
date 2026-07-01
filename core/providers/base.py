from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Retorna o nome do provedor."""

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Envia uma requisição de chat completion para o provedor de LLM."""

    @abstractmethod
    def unload_model(self, model: str) -> dict[str, Any]:
        """Descarrega o modelo da memória do provedor."""
