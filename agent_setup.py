import getpass
from datetime import datetime
from pathlib import Path
from typing import Annotated

from core import AgentBuilder, Agent


def create_agent() -> Agent:
    """Configura e retorna uma instância do Agent pré-configurada com ferramentas e contexto."""
    agent = AgentBuilder().build()
    workspace_dir = Path("workspace")

    @agent.context
    def user_context() -> str:
        return (
            f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
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
        """Get a list of files in the 'workspace' directory."""
        if not workspace_dir.exists():
            try:
                workspace_dir.mkdir()
            except Exception as e:
                return [f"Error creating directory: {str(e)}"]

        try:
            return [
                str(f.relative_to(workspace_dir))
                for f in workspace_dir.rglob("*")
                if f.is_file()
            ]
        except Exception as e:
            return [f"Error listing directory: {str(e)}"]

    @agent.tool
    def read_file(
        file_path: Annotated[str, "The relative path of the file to read"],
    ) -> str:
        """Read the content of a file in the 'workspace' directory."""
        file_path = Path(file_path.strip())
        if file_path.is_absolute():
            return (
                "Error: file_path must be a relative path within the 'workspace' directory."
            )
        full_path = workspace_dir / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @agent.tool
    def write_file(
        file_path: Annotated[str, "The relative path of the file to write"],
        content: Annotated[str, "The content to write to the file"],
    ) -> str:
        """Write content to a file in the 'workspace' directory."""
        file_path = Path(file_path.strip())
        if file_path.is_absolute():
            return (
                "Error: file_path must be a relative path within the 'workspace' directory."
            )
        full_path = workspace_dir / file_path

        try:
            if not full_path.parent.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"Error creating directory: {str(e)}"

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File '{file_path}' written successfully."
        except Exception as e:
            return f"Error writing file: {str(e)}"

    return agent
