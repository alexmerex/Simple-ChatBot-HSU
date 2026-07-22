import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chatbot_hsu.config import ChatbotConfig  # noqa: E402
from chatbot_hsu.engine import ChatbotEngine  # noqa: E402
from chatbot_hsu.history import (  # noqa: E402
    HistoryTurn,
    export_history_json,
    export_history_txt,
)
from chatbot_hsu.logging_utils import configure_logging  # noqa: E402


CLI_HELP = """Available commands:
  /help                Show this help
  /clear               Clear current session history
  /reload              Reload local + web index immediately
  /reindex-web         Rebuild web index only (force crawl)
  /config              Show current runtime config
  /topk [n]            Show/set top-k explanation rows in CLI
  /export json|txt     Export current history manually
  exit | quit          Exit CLI (auto-export history)
"""


def _print_topk(result, top_k: int):
    if not result.candidates:
        print("Top-k: no candidates")
        return

    for rank, c in enumerate(result.candidates[:top_k], start=1):
        print(
            f"#{rank} score={c.final_score:.4f} sim={c.similarity:.4f} lex={c.lexical_score:.4f} -> {c.answer}"
        )


def _print_config(engine: ChatbotEngine):
    snapshot = engine.config_snapshot()
    print("Current config:")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


def _auto_export_history(
    history: list[HistoryTurn], config: ChatbotConfig, source: str, session_id: str
) -> None:
    if not history:
        return

    json_path = export_history_json(
        history,
        config.history_export_dir,
        filename_prefix=f"{source}_auto",
        session_id=session_id,
        keep_last_exports=config.history_keep_last_exports,
    )
    txt_path = export_history_txt(
        history,
        config.history_export_dir,
        filename_prefix=f"{source}_auto",
        session_id=session_id,
        keep_last_exports=config.history_keep_last_exports,
    )
    print(f"Auto-exported history:\n  JSON: {json_path}\n  TXT: {txt_path}")


def run_cli(engine: ChatbotEngine, config: ChatbotConfig) -> None:
    session_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"ChatBot CLI mode. Session: {session_id}. Type 'exit' to quit.")
    print(CLI_HELP)

    history: list[HistoryTurn] = []
    topk_override: int | None = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if user_input.lower() in {"exit", "quit"}:
            print("Bye!")
            break

        if user_input.startswith("/"):
            cmd_parts = user_input.split()
            cmd = cmd_parts[0].lower()

            if cmd == "/help":
                print(CLI_HELP)
                continue

            if cmd == "/clear":
                history.clear()
                print("Session history cleared.")
                continue

            if cmd == "/reload":
                try:
                    engine.force_reload()
                    print("Reloaded local + web index.")
                except (FileNotFoundError, ValueError) as exc:
                    print(f"Reload failed: {exc}")
                continue

            if cmd == "/reindex-web":
                try:
                    engine.reindex_web()
                    print("Web index rebuilt.")
                except (FileNotFoundError, ValueError) as exc:
                    print(f"Web reindex failed: {exc}")
                continue

            if cmd == "/config":
                _print_config(engine)
                continue

            if cmd == "/topk":
                if len(cmd_parts) == 2:
                    try:
                        topk_override = max(1, int(cmd_parts[1]))
                        print(f"Top-k display set to {topk_override}")
                    except ValueError:
                        print("Usage: /topk [n]")
                else:
                    current = (
                        topk_override if topk_override is not None else config.explanation_top_k
                    )
                    print(f"Current top-k display: {current}")
                continue

            if cmd == "/export" and len(cmd_parts) == 2:
                if not history:
                    print("No history to export yet.")
                    continue
                kind = cmd_parts[1].lower()
                if kind == "json":
                    output = export_history_json(
                        history,
                        config.history_export_dir,
                        session_id=session_id,
                        keep_last_exports=config.history_keep_last_exports,
                    )
                    print(f"Exported JSON: {output}")
                elif kind == "txt":
                    output = export_history_txt(
                        history,
                        config.history_export_dir,
                        session_id=session_id,
                        keep_last_exports=config.history_keep_last_exports,
                    )
                    print(f"Exported TXT: {output}")
                else:
                    print("Usage: /export json|txt")
                continue

            print("Unknown command. Type /help")
            continue

        try:
            result = engine.ask(user_input)
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"Request failed: {exc}")
            continue
        print(f"Bot: {result.answer}")

        if result.citation_urls:
            print("Citations:")
            for url in result.citation_urls:
                print(f" - {url}")

        history.append(
            HistoryTurn(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                user=user_input,
                bot=result.answer,
                similarity=result.similarity,
                index=result.index,
                used_fallback=result.used_fallback,
                citation_urls=result.citation_urls or [],
            )
        )

        if config.debug:
            print(
                f"Debug: similarity={result.similarity:.4f}, index={result.index}, fallback={result.used_fallback}"
            )

        if config.show_explanations and result.candidates:
            display_k = topk_override if topk_override is not None else config.explanation_top_k
            print("Explain: Top candidates")
            _print_topk(result, display_k)

    try:
        _auto_export_history(history, config, source="cli", session_id=session_id)
    except OSError as exc:
        print(f"Auto-export failed: {exc}", file=sys.stderr)


def run_gui(engine: ChatbotEngine, config: ChatbotConfig) -> None:
    from chatbot_hsu.gui import ChatBotApp

    app = ChatBotApp(engine=engine, config=config)
    app.run()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HSU ChatBot")
    parser.add_argument("--mode", choices=["gui", "cli"], help="Override mode from .env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        config = ChatbotConfig()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return

    if args.mode:
        config.mode = args.mode

    for attribute in ("knowledge_file", "history_export_dir", "web_index_dir"):
        path = getattr(config, attribute)
        if not path.is_absolute():
            setattr(config, attribute, ROOT_DIR / path)

    configure_logging(level=config.log_level, debug=config.debug)

    try:
        engine = ChatbotEngine(config)
    except (OSError, RuntimeError, ValueError) as exc:
        if config.mode == "gui":
            from tkinter import Tk, messagebox

            root = Tk()
            root.withdraw()
            messagebox.showerror("Startup error", str(exc))
            root.destroy()
        else:
            print(f"Startup error: {exc}")
        return

    if config.mode == "cli":
        run_cli(engine, config)
    else:
        run_gui(engine, config)


if __name__ == "__main__":
    main()
