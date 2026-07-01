import json
import platform
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from rich.console import Console

from core.commands.base import Command, CommandAction


class HelpCommand(Command):
    @property
    def name(self) -> str:
        return "/help"

    @property
    def description(self) -> str:
        return "Show this help message"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        from core.commands.registry import CommandRegistry

        # Coleta e ordena os comandos únicos registrados
        cmds = CommandRegistry.get_all_commands()
        help_lines = [f"**{cmd.name}** - {cmd.description}" for cmd in cmds]
        console.print("### 📚 Comandos Disponíveis:\n---\n" + "\n\n".join(help_lines))
        return CommandAction.CONTINUE


class ClearCommand(Command):
    @property
    def name(self) -> str:
        return "/clear"

    @property
    def description(self) -> str:
        return "Clear conversation history"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        agent.messages.clear()
        console.print("Conversation history cleared.")
        return CommandAction.CONTINUE


class UnloadCommand(Command):
    @property
    def name(self) -> str:
        return "/unload"

    @property
    def description(self) -> str:
        return "Unload the model from backend"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        agent.unload_model()
        console.print("Model unloaded successfully.")
        return CommandAction.CONTINUE


class ExportCommand(Command):
    @property
    def name(self) -> str:
        return "/export"

    @property
    def description(self) -> str:
        return "Export conversation to file (json|txt)"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        if len(args) == 1:
            file_type = args[0].strip().lower()
        else:
            console.print("Enter file type (txt, json): ", end="")
            file_type = console.input().strip().lower()

        if file_type not in ("json", "txt"):
            file_type = "txt"

        output_dir = Path("exports")
        output_dir.mkdir(exist_ok=True)
        basename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if file_type == "json":
            export_path = output_dir / f"{basename}.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(agent.messages, f, indent=2)
        else:
            export_path = output_dir / f"{basename}.txt"
            with open(export_path, "w", encoding="utf-8") as f:
                for msg in agent.messages:
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    f.write(f"{role}: {content}\n")

        # Verifica se está rodando via MockConsole (GUI)
        is_gui = console.__class__.__name__ == "MockConsole"
        if is_gui:
            console.print(
                f"Conversation successfully exported. [Baixar Arquivo {file_type.upper()}](/exports/{export_path.name})"
            )
        else:
            console.print(f"Conversation exported to {export_path}")

        return CommandAction.CONTINUE


class ModelCommand(Command):
    @property
    def name(self) -> str:
        return "/model"

    @property
    def description(self) -> str:
        return "Change LLM model in real-time (ex: /model llama3)"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        if not args:
            console.print(
                f"Active model: `{agent.model}`. Use: `/model <model_name>` to change."
            )
            return CommandAction.CONTINUE
        new_model = args[0].strip()
        agent.model = new_model
        console.print(f"Model successfully changed to `{new_model}`.")
        return CommandAction.CONTINUE


class PromptCommand(Command):
    @property
    def name(self) -> str:
        return "/prompt"

    @property
    def description(self) -> str:
        return "Change system prompt (ex: /prompt You are a Python expert.)"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        if not args:
            console.print(
                f"Current System Prompt: `{agent.system_prompt}`. Use `/prompt <new prompt>` to change."
            )
            return CommandAction.CONTINUE
        new_prompt = " ".join(args).strip()
        agent.system_prompt = new_prompt
        console.print("System Prompt successfully updated.")
        return CommandAction.CONTINUE


class ViewCommand(Command):
    @property
    def name(self) -> str:
        return "/view"

    @property
    def description(self) -> str:
        return "View workspace file content (ex: /view script.py)"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        if not args:
            console.print("Please specify a filename: `/view <filename>`")
            return CommandAction.CONTINUE
        filename = args[0].strip()
        workspace_dir = Path("workspace")
        file_path = workspace_dir / filename

        try:
            resolved_path = file_path.resolve()
            resolved_dir = workspace_dir.resolve()
            if not str(resolved_path).startswith(str(resolved_dir)):
                console.print(
                    "Error: Access denied. File must be within the `workspace/` directory."
                )
                return CommandAction.CONTINUE
        except Exception:
            console.print("Error: Invalid path.")
            return CommandAction.CONTINUE

        if not file_path.exists() or not file_path.is_file():
            console.print(f"Error: File `{filename}` not found in the workspace.")
            return CommandAction.CONTINUE

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            suffix = file_path.suffix.lstrip(".") or "txt"
            console.print(f"### Conteúdo de `{filename}`:\n```{suffix}\n{content}\n```")
        except Exception as e:
            console.print(f"Error reading file: {str(e)}")

        return CommandAction.CONTINUE


class DeleteCommand(Command):
    @property
    def name(self) -> str:
        return "/delete"

    @property
    def description(self) -> str:
        return "Delete workspace file (ex: /delete script.py)"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        if not args:
            console.print("Please specify a filename: `/delete <filename>`")
            return CommandAction.CONTINUE
        filename = args[0].strip()
        workspace_dir = Path("workspace")
        file_path = workspace_dir / filename

        try:
            resolved_path = file_path.resolve()
            resolved_dir = workspace_dir.resolve()
            if not str(resolved_path).startswith(str(resolved_dir)):
                console.print(
                    "Error: Access denied. File must be within the `workspace/` directory."
                )
                return CommandAction.CONTINUE
        except Exception:
            console.print("Error: Invalid path.")
            return CommandAction.CONTINUE

        if not file_path.exists() or not file_path.is_file():
            console.print(f"Error: File `{filename}` not found in the workspace.")
            return CommandAction.CONTINUE

        try:
            file_path.unlink()
            console.print(f"File `{filename}` successfully deleted from workspace.")
        except Exception as e:
            console.print(f"Error deleting file: {str(e)}")

        return CommandAction.CONTINUE


class StatusCommand(Command):
    @property
    def name(self) -> str:
        return "/status"

    @property
    def description(self) -> str:
        return "Show detailed agent and system status"

    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        tools_count = len(agent.tools.tools)
        msg_count = len(agent.messages)
        prompt_len = len(agent.system_prompt)

        status_info = (
            f"### 📊 Status do Agente e Sistema\n"
            f"---\n"
            f"**Agente:**\n"
            f"- **Modelo:** `{agent.model}`\n"
            f"- **Provedor:** `{agent.provider.__class__.__name__}`\n"
            f"- **System Prompt:** `{prompt_len} caracteres`\n"
            f"- **Ferramentas Registradas:** `{tools_count}`\n"
            f"- **Total de Mensagens na Sessão:** `{msg_count}`\n\n"
            f"**Sistema:**\n"
            f"- **OS:** `{platform.system()} {platform.release()}`\n"
            f"- **Python:** `{platform.python_version()}`\n"
            f"- **PID do Processo:** `{os.getpid()}`\n"
            f"- **Diretório do Projeto:** `{Path.cwd()}`"
        )
        console.print(status_info)
        return CommandAction.CONTINUE
