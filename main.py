import getpass

from rich.console import Console
from typing import Annotated
from datetime import datetime
from pathlib import Path

from utils.agent import Agent
from utils.utils import commands_handler, CommandAction


def main():
    agent = Agent()
    console = Console()

    files_dir = Path("files")

    @agent.context
    def user_context() -> str:
        return (
            f"Current date and time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"Current user: {getpass.getuser()}\n"
            f"Current working directory: {Path.cwd()}"
        )

    @agent.tool
    def add(
        a: Annotated[int, "First number"],
        b: Annotated[int, "Second number"],
    ) -> int:
        """Add two numbers together."""
        return a + b

    @agent.tool
    def multiply(
        a: Annotated[int, "First number"],
        b: Annotated[int, "Second number"],
    ) -> int:
        """Multiply two numbers together."""
        return a * b

    @agent.tool
    def get_files() -> list[str]:
        """Get a list of files in the 'files' directory."""
        if not files_dir.exists():
            try:
                files_dir.mkdir()
            except Exception as e:
                return [f"Error creating directory: {str(e)}"]

        try:
            return [str(f) for f in files_dir.rglob("*")]
        except Exception as e:
            return [f"Error listing directory: {str(e)}"]

    @agent.tool
    def read_file(
        file_path: Annotated[str, "The path of the file to read"],
    ) -> str:
        """Read the content of a file in the 'files' directory."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @agent.tool
    def write_file(
        file_path: Annotated[str, "The relative path of the file to write"],
        content: Annotated[str, "The content to write to the file"],
    ) -> str:
        """Write content to a file in the 'files' directory."""
        file_path = Path(file_path.strip())
        if file_path.is_absolute():
            return (
                "Error: file_path must be a relative path within the 'files' directory."
            )
        full_path = files_dir / file_path

        try:
            if not full_path.parent.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"Error creating directory: {str(e)}"

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File '{full_path}' written successfully."
        except Exception as e:
            return f"Error writing file: {str(e)}"

    while True:
        console.print("[green]You:[/green] ", end="")

        try:
            user_input = console.input().strip()
        except KeyboardInterrupt, EOFError:
            console.print("\n[dim]Exiting...[/dim]")
            break

        if user_input[0] == "/":
            command, *args = user_input.lower().split()
            match commands_handler(command, args, agent, console):
                case CommandAction.CONTINUE:
                    continue
                case CommandAction.EXIT:
                    exit(0)

        with console.status("[dim]Thinking...[/dim]", spinner="arc") as status:
            response = agent.chat(user_input, status)

        console.print(f"[blue]Assistant:[/blue] {response}")


if __name__ == "__main__":
    main()
