from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from rich.console import Console


class CommandAction(Enum):
    CONTINUE = 1
    EXIT = 2


class Command(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """O nome/comando (ex: '/help')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """A descrição textual do comando para o menu de ajuda."""

    @abstractmethod
    def execute(self, agent: Any, console: Console, args: list[str]) -> CommandAction:
        """Executa a lógica associada ao comando."""
