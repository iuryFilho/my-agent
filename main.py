import requests
import json
from pathlib import Path
from rich.console import Console
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime


class CommandAction(Enum):
    CONTINUE = 1
    EXIT = 2


@dataclass
class Agent:
    model: str = "qwen/qwen3-vl-4b"
    base_url: str = "http://localhost:1234/v1"
    api_url: str = "http://localhost:1234/api/v1"
    api_key: str = field(default="NO_API_KEY", repr=False)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        r = requests.post(
            url,
            headers=headers,
            json={"model": self.model, "messages": self.messages},
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices")

        if not choices:
            raise RuntimeError("Model response missing choices")

        message = choices[0].get("message")
        if message is None:
            raise RuntimeError("Model response missing message")

        response = message.get("content") or ""
        self.messages.append({"role": "assistant", "content": response})
        return response

    def unload_model(self):
        url = f"{self.api_url}/models/unload"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {"instance_id": self.model}
        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()


def commands_handler(
    command: str, command_args: list[str], agent: Agent, console: Console
) -> CommandAction:
    match command:
        case "/help":
            console.print(
                "/help - Show this help message\n"
                "/clear - Clear conversation history\n"
                "/export [json|txt] - Export conversation to file\n"
                "/exit or /quit - Exit the program",
            )
            return CommandAction.CONTINUE

        case "/clear":
            agent.messages.clear()
            console.print("[dim]Conversation history cleared.[/dim]")
            return CommandAction.CONTINUE

        case "/unload":
            agent.unload_model()
            console.print("[dim]Model unloaded.[/dim]")
            return CommandAction.CONTINUE

        case "/export":
            if len(command_args) == 1:
                file_type = command_args[0].strip()
            else:
                console.print("Enter file type (txt, json): ", end="")
                file_type = console.input().strip().lower()

            with console.status("[dim]Exporting conversation...[/dim]", spinner="arc"):
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                basename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                if file_type == "json":
                    with open(
                        output_dir / f"{basename}.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(agent.messages, f, indent=2)
                else:
                    with open(
                        output_dir / f"{basename}.txt", "w", encoding="utf-8"
                    ) as f:
                        for msg in agent.messages:
                            role = msg["role"].capitalize()
                            content = msg["content"]
                            f.write(f"{role}: {content}\n")

            console.print(f"[dim]Conversation exported to {basename}.{file_type}[/dim]")
            return CommandAction.CONTINUE

        case "/exit" | "/quit":
            console.print("[dim]Goodbye![/dim]")
            return CommandAction.EXIT

        case _:
            console.print(
                "[red]Unknown command. Type /help for a list of commands.[/red]"
            )
            return CommandAction.CONTINUE


def main():
    agent = Agent()
    console = Console()

    while True:
        console.print("[green]You:[/green] ", end="")
        user_input = console.input().strip()
        if user_input[0] == "/":
            command, *args = user_input.lower().split()
            match commands_handler(command, args, agent, console):
                case CommandAction.CONTINUE:
                    continue
                case CommandAction.EXIT:
                    exit(0)

        with console.status("[dim]Thinking...[/dim]", spinner="arc"):
            response = agent.chat(user_input)

        console.print(f"[blue]Assistant:[/blue] {response}")


if __name__ == "__main__":
    main()
