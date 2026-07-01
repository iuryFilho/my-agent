import json
from dataclasses import dataclass, field
from typing import Callable, Any
from rich.status import Status

from core.tools import Tools
from core.providers import LLMProvider, OpenAICompatibleProvider

BASE_URL = "http://localhost:1234/v1"
BASE_API_URL = "http://localhost:1234/api/v1"


@dataclass
class Agent:
    system_prompt: str = "You are a helpful assistant."
    model: str = "qwen/qwen3-vl-4b"
    provider: LLMProvider = field(
        default_factory=lambda: OpenAICompatibleProvider(BASE_URL, BASE_API_URL)
    )
    tools: Tools = field(default_factory=Tools)
    contexts: dict[str, Callable[[], str]] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def tool(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorador para registrar uma ferramenta (tool) no agente."""
        return self.tools.register(func)

    def context(self, func: Callable[[], str]) -> Callable[[], str]:
        """Decorador para registrar um contexto dinâmico no agente."""
        self.contexts[func.__name__] = func
        return func

    def chat(self, user_message: str, status: Status) -> str:
        """Envia uma mensagem do usuário para o assistente e processa a resposta."""
        self.messages.append({"role": "user", "content": user_message})

        context_content = "\n\n".join(
            f"<context>\n<{n}>{fn()}</{n}>\n</context>"
            for n, fn in self.contexts.items()
        )

        prefix: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": context_content},
        ]

        while True:
            tool_schemas = self.tools.get_schemas()

            # Delega a geração da resposta do chat para o provedor de LLM injetado
            data = self.provider.chat_completion(
                model=self.model,
                messages=prefix + self.messages,
                tools=tool_schemas if tool_schemas else None,
            )

            choices = data.get("choices")
            if not choices:
                raise RuntimeError("Model response missing choices")

            message = choices[0].get("message")
            if message is None:
                raise RuntimeError("Model response missing message")

            tool_calls = message.get("tool_calls", [])
            response = message.get("content") or ""

            self.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                    "tool_calls": [
                        {
                            "id": tc.get("id"),
                            "type": tc.get("type"),
                            "function": {
                                "name": tc.get("function", {}).get("name"),
                                "arguments": tc.get("function", {}).get("arguments"),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            if not tool_calls:
                return response

            if response:
                old_status = status.status
                status.update(
                    f"{old_status}\n[dim][blue]Assistant:[/blue] {response}[/dim]"
                )

            for tool_call in tool_calls:
                result = self.tools.execute(tool_call)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result),
                    }
                )

    def unload_model(self) -> dict[str, Any]:
        """Descarrega o modelo atual do provedor configurado."""
        try:
            return self.provider.unload_model(self.model)
        except ValueError as e:
            return {"message": str(e)}


class AgentBuilder:
    """Implementação do Builder Pattern para facilitar a criação e configuração de instâncias do Agent."""

    def __init__(self) -> None:
        self._system_prompt: str = "You are a helpful assistant."
        self._model: str = "qwen/qwen3-vl-4b"
        self._provider: LLMProvider | None = None
        self._tools: Tools | None = None

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        self._system_prompt = prompt
        return self

    def with_model(self, model: str) -> "AgentBuilder":
        self._model = model
        return self

    def with_provider(self, provider: LLMProvider) -> "AgentBuilder":
        self._provider = provider
        return self

    def with_tools(self, tools: Tools) -> "AgentBuilder":
        self._tools = tools
        return self

    def build(self) -> Agent:
        provider = self._provider
        if provider is None:
            provider = OpenAICompatibleProvider(BASE_URL, BASE_API_URL)

        agent_args: dict[str, Any] = {
            "system_prompt": self._system_prompt,
            "model": self._model,
            "provider": provider,
        }
        if self._tools is not None:
            agent_args["tools"] = self._tools

        return Agent(**agent_args)
