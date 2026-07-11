import yaml
from pathlib import Path
from typing import Any
from core.agent import Agent, AgentBuilder
from core.providers.openai import OpenAICompatibleProvider


class Config:
    """Classe responsável por ler e interpretar as configurações do agente a partir de um arquivo YAML."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.model: str = data.get("model", "qwen/qwen3-vl-4b")
        self.system_prompt: str = data.get(
            "system_prompt", "You are a helpful assistant."
        )
        self.provider_settings: dict[str, Any] = data.get("provider", {})

    @classmethod
    def from_yaml(cls, filepath: str | Path) -> "Config":
        """Carrega e analisa um arquivo de configuração YAML."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)

    def build_agent(self) -> Agent:
        """Constrói uma instância de Agent configurada com base nas definições carregadas."""
        builder = AgentBuilder()
        builder.with_model(self.model)
        builder.with_system_prompt(self.system_prompt)

        provider_name = self.provider_settings.get("name", "openai")
        if provider_name == "openai":
            base_url = self.provider_settings.get(
                "base_url", "http://localhost:1234/v1"
            )
            base_api_url = self.provider_settings.get(
                "base_api_url", "http://localhost:1234/api/v1"
            )
            api_key = self.provider_settings.get("api_key", "NO_API_KEY")

            provider = OpenAICompatibleProvider(
                base_url=base_url,
                base_api_url=base_api_url,
                api_key=api_key,
            )
            builder.with_provider(provider)

        return builder.build()
