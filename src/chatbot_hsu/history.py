import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class HistoryTurn:
    timestamp: str
    user: str
    bot: str
    similarity: float
    index: int
    used_fallback: bool


def _ensure_export_dir(export_dir: Path) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def prune_old_exports(export_dir: Path, keep_last: int = 20) -> int:
    export_dir = _ensure_export_dir(export_dir)
    if keep_last <= 0:
        keep_last = 1

    files = sorted(
        [f for f in export_dir.iterdir() if f.is_file() and f.suffix.lower() in {".json", ".txt"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    to_delete = files[keep_last:]
    for file_path in to_delete:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            continue

    return len(to_delete)


def export_history_json(
    history: list[HistoryTurn],
    export_dir: Path,
    filename_prefix: str = "chat_history",
    session_id: str | None = None,
    keep_last_exports: int = 20,
) -> Path:
    export_dir = _ensure_export_dir(export_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_part = f"-{session_id}" if session_id else ""
    output = export_dir / f"{filename_prefix}{session_part}-{stamp}.json"

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "turn_count": len(history),
        "history": [asdict(item) for item in history],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    prune_old_exports(export_dir, keep_last=keep_last_exports)
    return output


def export_history_txt(
    history: list[HistoryTurn],
    export_dir: Path,
    filename_prefix: str = "chat_history",
    session_id: str | None = None,
    keep_last_exports: int = 20,
) -> Path:
    export_dir = _ensure_export_dir(export_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_part = f"-{session_id}" if session_id else ""
    output = export_dir / f"{filename_prefix}{session_part}-{stamp}.txt"

    lines: list[str] = []
    if session_id:
        lines.append(f"Session: {session_id}")
        lines.append("")

    for idx, turn in enumerate(history, start=1):
        lines.append(f"[{idx}] {turn.timestamp}")
        lines.append(f"User: {turn.user}")
        lines.append(f"Bot: {turn.bot}")
        lines.append(
            f"Meta: similarity={turn.similarity:.4f}, index={turn.index}, fallback={turn.used_fallback}"
        )
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    prune_old_exports(export_dir, keep_last=keep_last_exports)
    return output
