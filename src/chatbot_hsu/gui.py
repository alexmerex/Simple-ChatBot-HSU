from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from .config import ChatbotConfig
from .engine import ChatbotEngine, RetrievalResult
from .history import HistoryTurn, export_history_json, export_history_txt


class ChatBotApp:
    def __init__(self, engine: ChatbotEngine, config: ChatbotConfig):
        self.engine = engine
        self.config = config
        self.history: list[HistoryTurn] = []
        self.session_id = f"gui-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self.window = tk.Tk()
        self.window.title(f"{config.app_title} | Session: {self.session_id}")
        self.window.geometry("1200x700")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.main_frame = tk.Frame(self.window)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.chat_display = scrolledtext.ScrolledText(
            self.main_frame,
            width=80,
            height=24,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.chat_display.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.explain_panel = scrolledtext.ScrolledText(
            self.main_frame,
            width=50,
            height=24,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.explain_panel.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")

        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

        self.user_entry = tk.Entry(self.bottom_frame, width=100)
        self.user_entry.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.send_button = tk.Button(self.bottom_frame, text="Send", command=self.on_send)
        self.send_button.grid(row=0, column=1, padx=(0, 8))

        self.clear_button = tk.Button(
            self.bottom_frame, text="Clear Chat", command=self.on_clear_chat
        )
        self.clear_button.grid(row=0, column=2, padx=(0, 8))

        self.reload_button = tk.Button(
            self.bottom_frame, text="Reload Knowledge", command=self.on_reload_knowledge
        )
        self.reload_button.grid(row=0, column=3, padx=(0, 8))

        self.export_json_button = tk.Button(
            self.bottom_frame,
            text="Export JSON",
            command=self.on_export_json,
        )
        self.export_json_button.grid(row=0, column=4, padx=(0, 8))

        self.export_txt_button = tk.Button(
            self.bottom_frame,
            text="Export TXT",
            command=self.on_export_txt,
        )
        self.export_txt_button.grid(row=0, column=5)

        self.user_entry.bind("<Return>", self.on_send)

        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=2)
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=0)
        self.bottom_frame.columnconfigure(0, weight=1)

        self._append_explain("Session", self.session_id)
        self._append_explain("Explanations", "Top-k candidates will appear here.")

    def _append_chat(self, speaker: str, text: str) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{speaker}: {text}\n")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _set_explanations(self, result: RetrievalResult) -> None:
        self.explain_panel.configure(state=tk.NORMAL)
        self.explain_panel.delete("1.0", tk.END)

        self.explain_panel.insert(tk.END, f"Session: {self.session_id}\n")

        if result.citation_urls:
            self.explain_panel.insert(tk.END, "Citations\n")
            self.explain_panel.insert(tk.END, "=" * 60 + "\n")
            for url in result.citation_urls:
                self.explain_panel.insert(tk.END, f"- {url}\n")
            self.explain_panel.insert(tk.END, "\n")

        if not self.config.show_explanations or not result.candidates:
            self.explain_panel.insert(tk.END, "Explanations disabled or no candidates.\n")
        else:
            self.explain_panel.insert(tk.END, "Top candidates\n")
            self.explain_panel.insert(tk.END, "=" * 60 + "\n")
            for rank, c in enumerate(result.candidates, start=1):
                self.explain_panel.insert(
                    tk.END,
                    (
                        f"#{rank}\n"
                        f"score={c.final_score:.4f} | sim={c.similarity:.4f} | lex={c.lexical_score:.4f}\n"
                        f"answer={c.answer}\n\n"
                    ),
                )

        self.explain_panel.configure(state=tk.DISABLED)
        self.explain_panel.see(tk.END)

    def _append_explain(self, title: str, text: str) -> None:
        self.explain_panel.configure(state=tk.NORMAL)
        self.explain_panel.insert(tk.END, f"{title}: {text}\n")
        self.explain_panel.configure(state=tk.DISABLED)
        self.explain_panel.see(tk.END)

    def _record_history(self, user: str, result: RetrievalResult) -> None:
        self.history.append(
            HistoryTurn(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                user=user,
                bot=result.answer,
                similarity=result.similarity,
                index=result.index,
                used_fallback=result.used_fallback,
                citation_urls=result.citation_urls or [],
            )
        )

    def _choose_export_dir(self):
        chosen = filedialog.askdirectory(title="Select export folder")
        if not chosen:
            return self.config.history_export_dir
        return self.config.history_export_dir.__class__(chosen)

    def _export_history_auto(self) -> tuple[str, str] | tuple[None, None]:
        if not self.history:
            return (None, None)

        json_path = export_history_json(
            self.history,
            self.config.history_export_dir,
            filename_prefix="gui_auto",
            session_id=self.session_id,
            keep_last_exports=self.config.history_keep_last_exports,
        )
        txt_path = export_history_txt(
            self.history,
            self.config.history_export_dir,
            filename_prefix="gui_auto",
            session_id=self.session_id,
            keep_last_exports=self.config.history_keep_last_exports,
        )
        return (str(json_path), str(txt_path))

    def on_send(self, event=None):
        user_input = self.user_entry.get().strip()

        if not user_input:
            messagebox.showwarning("Warning", "Please enter a question.")
            return

        try:
            result = self.engine.ask(user_input)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Request failed", str(exc))
            return

        self._append_chat("User", user_input)
        self._append_chat("ChatBot", result.answer)

        if self.config.debug:
            self._append_chat(
                "Debug",
                f"similarity={result.similarity:.4f}, index={result.index}, fallback={result.used_fallback}",
            )

        self._set_explanations(result)
        self._record_history(user_input, result)

        self._append_chat("", "")
        self.user_entry.delete(0, tk.END)

    def on_clear_chat(self):
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)

        self.explain_panel.configure(state=tk.NORMAL)
        self.explain_panel.delete("1.0", tk.END)
        self.explain_panel.insert(tk.END, f"Session: {self.session_id}\n")
        self.explain_panel.insert(tk.END, "Explanations cleared.\n")
        self.explain_panel.configure(state=tk.DISABLED)

        self.history.clear()

    def on_reload_knowledge(self):
        try:
            self.engine.force_reload()
            messagebox.showinfo("Reload", "Knowledge reloaded successfully.")
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Reload failed", str(exc))

    def on_export_json(self):
        if not self.history:
            messagebox.showinfo("Export", "No history to export yet.")
            return

        export_dir = self._choose_export_dir()
        try:
            output = export_history_json(
                self.history,
                export_dir,
                session_id=self.session_id,
                keep_last_exports=self.config.history_keep_last_exports,
            )
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo("Export", f"Exported JSON to:\n{output}")

    def on_export_txt(self):
        if not self.history:
            messagebox.showinfo("Export", "No history to export yet.")
            return

        export_dir = self._choose_export_dir()
        try:
            output = export_history_txt(
                self.history,
                export_dir,
                session_id=self.session_id,
                keep_last_exports=self.config.history_keep_last_exports,
            )
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo("Export", f"Exported TXT to:\n{output}")

    def on_close(self):
        try:
            self._export_history_auto()
        except OSError as exc:
            messagebox.showwarning("Auto-export failed", str(exc))
        self.window.destroy()

    def run(self) -> None:
        self.window.mainloop()
