"""Thin UI wrapper around rich with a plain-text fallback."""
from __future__ import annotations

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown

    console = Console()
    _RICH = True
except Exception:
    console = None
    _RICH = False


def _print(msg: str = "") -> None:
    if _RICH:
        console.print(msg)
    else:
        print(msg)


def section(title: str) -> None:
    bar = "=" * 64
    _print(f"[bold cyan]{bar}[/]" if _RICH else bar)
    _print(f"[bold cyan]{title}[/]" if _RICH else title)
    _print(f"[bold cyan]{bar}[/]" if _RICH else bar)


def question(text: str) -> None:
    if _RICH:
        console.print(Panel(Markdown(text), title="QUESTION", border_style="yellow"))
    else:
        print("\n--- QUESTION ---")
        print(text)
        print("----------------\n")


def ok(msg: str) -> None:
    _print(f"[bold green]PASS[/] {msg}" if _RICH else f"PASS {msg}")


def fail(msg: str) -> None:
    _print(f"[bold red]FAIL[/] {msg}" if _RICH else f"FAIL {msg}")


def warn(msg: str) -> None:
    _print(f"[bold yellow]![/] {msg}" if _RICH else f"! {msg}")


def hint(msg: str) -> None:
    _print(f"[bold magenta]HINT[/] {msg}" if _RICH else f"HINT {msg}")


def info(msg: str) -> None:
    _print(f"[dim]{msg}[/]" if _RICH else msg)


def banner(text: str) -> None:
    if _RICH:
        console.print(Panel(text, border_style="cyan"))
    else:
        print(f"\n### {text} ###\n")


def prompt() -> str:
    return "cka-sim> "


def out(text: str) -> None:
    _print(text)
