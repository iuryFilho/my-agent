import contextlib
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_setup import create_agent
from core import CommandRegistry, CommandAction

# Cria a aplicação FastAPI
app = FastAPI(title="AI Agent Interface", version="1.0.0")

# Instancia o agente pré-configurado de forma global
agent = create_agent()


class ChatRequest(BaseModel):
    message: str


class MockStatus:
    def __init__(self, initial: str = ""):
        self.status = initial
        self.updates = []

    def update(self, text: str):
        self.status = text
        self.updates.append(text)


class MockConsole:
    def __init__(self):
        self.output_lines = []

    def print(self, *args, **kwargs):
        # Combina os argumentos e armazena a saída
        text = " ".join(str(arg) for arg in args)
        self.output_lines.append(text)

    def input(self, prompt=""):
        # Retorno padrão para evitar bloqueio da thread em ambiente web
        return "json"

    @contextlib.contextmanager
    def status(self, status_text, spinner=None):
        yield MockStatus(status_text)


# Garante que as pastas workspace e exports existem
WORKSPACE_DIR = Path("workspace")
EXPORTS_DIR = Path("exports")

WORKSPACE_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)


@app.get("/")
def get_index():
    """Serve a página principal do chat."""
    index_path = Path("static/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend static files not found.")
    return FileResponse(index_path)


@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    """Processa mensagens do usuário ou comandos da CLI."""
    user_input = request.message.strip()
    if not user_input:
        return {"response": "", "history": agent.messages, "is_command": False}

    # Verifica se é um comando CLI (/help, /clear, etc.)
    if user_input.startswith("/"):
        parts = user_input.lower().split()
        command_name = parts[0]
        args = parts[1:]

        cmd = CommandRegistry.get(command_name)
        if cmd:
            mock_console = MockConsole()
            action = cmd.execute(agent, mock_console, args)
            console_output = "\n".join(mock_console.output_lines)
            return {
                "response": console_output,
                "history": agent.messages,
                "is_command": True,
                "action": action.name,
            }
        else:
            return {
                "response": "[red]Unknown command. Type /help for a list of commands.[/red]",
                "history": agent.messages,
                "is_command": True,
            }

    # Fluxo normal de chat com o Agente
    mock_status = MockStatus("Thinking...")
    try:
        response = agent.chat(user_input, mock_status)
        return {
            "response": response,
            "history": agent.messages,
            "is_command": False,
            "status_updates": mock_status.updates,
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "history": agent.messages,
            "is_command": False,
        }


@app.get("/api/files")
def list_files():
    """Retorna a lista de arquivos no diretório 'workspace/'."""
    try:
        files = []
        for file in WORKSPACE_DIR.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(WORKSPACE_DIR)
                files.append(
                    {
                        "name": str(rel_path),
                        "size": file.stat().st_size,
                        "path": str(file.absolute()),
                    }
                )
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tools")
def list_tools():
    """Lista as ferramentas registradas no agente com suas respectivas assinaturas."""
    try:
        schemas = agent.tools.get_schemas()
        tools_list = []
        for s in schemas:
            func_data = s.get("function", {})
            tools_list.append(
                {
                    "name": func_data.get("name"),
                    "description": func_data.get("description"),
                    "parameters": func_data.get("parameters", {}).get("properties", {}),
                }
            )
        return {"tools": tools_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
def get_status():
    """Retorna o status geral de configuração do agente."""
    return {
        "model": agent.model,
        "system_prompt": agent.system_prompt,
        "provider": agent.provider.name,
        "total_messages": len(agent.messages),
    }


@app.get("/api/commands")
def list_commands():
    """Retorna a lista de comandos CLI registrados no sistema."""
    try:
        cmds = CommandRegistry.get_all_commands()
        return {
            "commands": [
                {"name": cmd.name, "description": cmd.description} for cmd in cmds
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Monta as pastas static e exports para servir arquivos estáticos e downloads
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
