import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key
import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

CONFIG_DIR = Path.home() / ".gemini_chat_cli"
ENV_FILE = CONFIG_DIR / ".env"
HISTORY_FILE = CONFIG_DIR / "chat_history.json"
MAX_HISTORY_TOKENS = 4000

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

console = Console()

load_dotenv(dotenv_path=ENV_FILE)

GEMINI_MODEL_ID = "gemini"
GEMINI_DEFAULT_MODEL_NAME = "gemini-1.5-flash"
GEMINI_ENV_VAR = "GEMINI_API_KEY"
GEMINI_SERVICE_NAME = "Google Gemini"

def get_api_key(service_name, env_var_name):
    """Gets API key from env, prompts user if not found, and offers to save."""
    api_key = os.getenv(env_var_name)
    if not api_key:
        console.print(f"[yellow]API key for {service_name} ({env_var_name}) not found.[/yellow]")
        api_key = console.input(f"Enter your {service_name} API key: ").strip()
        if api_key:
            save_choice = console.input(f"Save this key to {ENV_FILE}? (y/n): ").lower()
            if save_choice == 'y':
                if not ENV_FILE.exists():
                    ENV_FILE.touch()
                set_key(ENV_FILE, env_var_name, api_key)
                console.print(f"[green]API key for {service_name} saved.[/green]")
                os.environ[env_var_name] = api_key
            else:
                 console.print(f"[yellow]API key not saved. It will be used for this session only.[/yellow]")
        else:
            console.print(f"[red]No API key entered for {service_name}. The application cannot continue.[/red]")
            return None
    return api_key

def initialize_gemini():
    """Initialize Google Gemini client."""
    api_key = get_api_key(GEMINI_SERVICE_NAME, GEMINI_ENV_VAR)
    if not api_key:
        return False

    try:
        genai.configure(api_key=api_key)

        console.print("[green]Google Gemini client configured.[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to configure Google Gemini: {e}[/red]")
        if "API key not valid" in str(e):
             console.print("[bold red]Please check if your GEMINI_API_KEY is correct.[/bold red]")
        return False

conversation_history = []

def add_to_history(role, text):
    """Adds a message to the conversation history."""
    role = "model" if role == "assistant" else role
    conversation_history.append({"role": role, "parts": [text]})

    while len(json.dumps(conversation_history)) > MAX_HISTORY_TOKENS and len(conversation_history) > 1:
         if len(conversation_history) >= 2:
             del conversation_history[0:2]
         else:
             break

def get_formatted_history():
    """Returns the history in the format Gemini expects."""
    return conversation_history

def ask_gemini(user_prompt):
    """Handles calls for Google Gemini."""
    formatted_history = get_formatted_history()

    try:
        console.print(f"_[dim]Calling Gemini ({GEMINI_DEFAULT_MODEL_NAME})...[/dim]_")
        model = genai.GenerativeModel(GEMINI_DEFAULT_MODEL_NAME)

        chat = model.start_chat(history=formatted_history)

        response = chat.send_message(user_prompt)

        ai_response = response.text

        add_to_history("user", user_prompt)
        add_to_history("model", ai_response)

        return ai_response
    except Exception as e:
         error_message = f"Error calling Gemini API: {e}"
         if hasattr(e, 'message'):
              error_message = f"Error calling Gemini API: {e.message}"

         if "API key not valid" in str(e) or (hasattr(e, 'message') and "API key not valid" in e.message):
              console.print(f"[bold red]Authentication Error. Check your API key.[/bold red]")
         elif "quota" in str(e).lower() or (hasattr(e, 'message') and "quota" in e.message.lower()):
              console.print(f"[bold red]Quota exceeded. Check your usage limits.[/bold red]")
         elif "Resource has been exhausted" in str(e):
              console.print(f"[bold red]Resource exhausted (e.g., usage quota). Check Gemini dashboard.[/bold red]")
         elif "billing account" in str(e).lower():
              console.print(f"[bold red]Billing account issue. Check your Google Cloud project.[/bold red]")
         else:
            console.print(f"[red]{error_message}[/red]")
         return None


def display_help():
    """Displays available commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    console.print("  /help          - Show this help message.")
    console.print("  /quit          - Exit the chatroom.")
    console.print("  /clear         - Clear the conversation history.")
    console.print("  /history       - Show the current conversation history.")
    console.print("  Anything else  - Send as a message to Gemini.\n")

def main():
    global conversation_history

    console.print(Panel(f"[bold magenta]Welcome to the Gemini Chat CLI![/bold magenta]\nUsing model: {GEMINI_DEFAULT_MODEL_NAME}\nType '/help' for commands.", border_style="blue"))

    if not initialize_gemini():
        console.print(f"[bold red]Exiting application. Gemini could not be initialized.[/bold red]")
        console.print(f"Make sure your API key is correct and saved in: {ENV_FILE}")
        return

    console.print(f"Starting chat with: [bold green]{GEMINI_SERVICE_NAME}[/bold green]")

    while True:
        try:
            prompt = console.input("[bold cyan]You:[/bold cyan] ")

            if not prompt.strip():
                continue

            if prompt.strip().lower() == "/quit":
                console.print("[bold magenta]Goodbye![/bold magenta]")
                break
            elif prompt.strip().lower() == "/help":
                display_help()
                continue
            elif prompt.strip().lower() == "/clear":
                 conversation_history = []
                 console.print(f"[yellow]Conversation history cleared.[/yellow]")
                 continue
            elif prompt.strip().lower() == "/history":
                 if conversation_history:
                      console.print(f"\n[bold yellow]Current History:[/bold yellow]")
                      for msg in conversation_history:
                           text = msg['parts'][0] if msg['parts'] else ""
                           role_color = "cyan" if msg['role'] == 'user' else "green"
                           console.print(f"[bold {role_color}]{msg['role'].capitalize()}:[/bold {role_color}] {text}")
                      console.print("-" * 20)
                 else:
                      console.print(f"[yellow]History is empty.[/yellow]")
                 continue

            ai_response = ask_gemini(prompt)

            if ai_response:
                 md = Markdown(ai_response)
                 console.print(f"[bold green]Gemini:[/bold green]")
                 console.print(md)
                 console.print("-" * 30)

        except EOFError:
            console.print("\n[bold magenta]Goodbye![/bold magenta]")
            break
        except KeyboardInterrupt:
            console.print("\n[bold magenta]Interrupted. Goodbye![/bold magenta]")
            break
        except Exception as e:
            console.print(f"\n[bold red]An unexpected error occurred in the main loop: {e}[/bold red]")

if __name__ == "__main__":
    main()
