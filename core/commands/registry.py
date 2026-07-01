from typing import ClassVar
from core.commands.base import Command
from core.commands.impl import (
    HelpCommand,
    ClearCommand,
    UnloadCommand,
    ExportCommand,
    ModelCommand,
    PromptCommand,
    ViewCommand,
    DeleteCommand,
    StatusCommand,
)


class CommandRegistry:
    _commands: ClassVar[dict[str, Command]] = {}

    @classmethod
    def register(cls, command: Command) -> None:
        """Registra um comando no sistema."""
        cls._commands[command.name] = command

    @classmethod
    def get(cls, name: str) -> Command | None:
        """Retorna um comando registrado pelo nome."""
        return cls._commands.get(name)

    @classmethod
    def get_all_commands(cls) -> list[Command]:
        """Retorna a lista de todos os comandos registrados de forma única."""
        seen = set()
        result = []
        # Mantém a ordem em que foram inseridos no dicionário
        for cmd in cls._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return result


# Registro padrão de comandos integrados do sistema
CommandRegistry.register(HelpCommand())
CommandRegistry.register(ClearCommand())
CommandRegistry.register(UnloadCommand())
CommandRegistry.register(ExportCommand())
CommandRegistry.register(ModelCommand())
CommandRegistry.register(PromptCommand())
CommandRegistry.register(ViewCommand())
CommandRegistry.register(DeleteCommand())
CommandRegistry.register(StatusCommand())
