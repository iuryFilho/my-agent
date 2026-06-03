import json

from rich.console import Console
from datetime import datetime
from pathlib import Path
from enum import Enum

from utils.agent import Agent


class CommandAction(Enum):
    CONTINUE = 1
    EXIT = 2


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
                output_dir = Path("exports")
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
