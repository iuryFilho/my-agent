import json
import requests

from dataclasses import dataclass, field
from typing import Callable, Any
from rich.status import Status

from utils.tools import Tools


@dataclass
class Agent:
    system_prompt: str = "You are a helpful assistant."
    model: str = "qwen/qwen3-vl-4b"
    base_url: str = "http://localhost:1234/v1"
    base_api_url: str = "http://localhost:1234/api/v1"
    api_key: str = field(default="NO_API_KEY", repr=False)
    tools: Tools = field(default_factory=Tools)
    contexts: dict[str, Callable[[], str]] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    def tool(self, func: Callable[..., Any]) -> Callable[..., Any]:
        return self.tools.register(func)

    def context(self, func: Callable[[], str]) -> Callable[[], str]:
        self.contexts[func.__name__] = func
        return func

    def chat(self, user_message: str, status: Status) -> str:
        self.messages.append({"role": "user", "content": user_message})

        context_content = "\n\n".join(
            f"<context>\n<{n}>{fn()}</{n}>\n</context>"
            for n, fn in self.contexts.items()
        )

        prefix: list[dict[str, any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": context_content},
        ]

        while True:
            api_kwargs = {
                "model": self.model,
                "messages": prefix + self.messages,
            }

            tool_schemas = self.tools.get_schemas()
            if tool_schemas:
                api_kwargs["tools"] = tool_schemas

            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            r = requests.post(url, headers=headers, json=api_kwargs, timeout=300)
            r.raise_for_status()
            data = r.json()
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

    def unload_model(self):
        url = f"{self.base_api_url}/models/unload"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {"instance_id": self.model}
        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()
