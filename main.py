from rich.console import Console
from agent_setup import create_agent
from core import CommandRegistry, CommandAction


def main():
    agent = create_agent()
    console = Console()

    while True:
        console.print("[green]You:[/green] ", end="")

        try:
            user_input = console.input().strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting...[/dim]")
            break

        if not user_input:
            continue

        if user_input[0] == "/":
            command, *args = user_input.lower().split()
            cmd = CommandRegistry.get(command)
            if cmd:
                action = cmd.execute(agent, console, args)
                if action == CommandAction.EXIT:
                    exit(0)
                elif action == CommandAction.CONTINUE:
                    continue
            else:
                console.print(
                    "[red]Unknown command. Type /help for a list of commands.[/red]"
                )
                continue

        with console.status("[dim]Thinking...[/dim]", spinner="arc") as status:
            response = agent.chat(user_input, status)

        console.print(f"[blue]Assistant:[/blue] {response}")


if __name__ == "__main__":
    main()
