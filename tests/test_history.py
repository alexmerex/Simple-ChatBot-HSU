import json
import os
from pathlib import Path

from chatbot_hsu.history import (
    HistoryTurn,
    export_history_json,
    export_history_txt,
    prune_old_exports,
)


def _turn() -> HistoryTurn:
    return HistoryTurn(
        timestamp="2026-07-22T12:00:00",
        user="Thông tin tuyển sinh?",
        bot="Nội dung tuyển sinh.",
        similarity=0.9,
        index=1,
        used_fallback=False,
        citation_urls=["https://www.hoasen.edu.vn/tuyen-sinh"],
    )


def test_history_exports_include_session_and_citations(tmp_path: Path):
    json_path = export_history_json([_turn()], tmp_path, session_id="test")
    txt_path = export_history_txt([_turn()], tmp_path, session_id="test")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["session_id"] == "test"
    assert payload["history"][0]["citation_urls"] == _turn().citation_urls
    assert "Citations: https://www.hoasen.edu.vn/tuyen-sinh" in txt_path.read_text(encoding="utf-8")


def test_prune_old_exports_keeps_newest_files(tmp_path: Path):
    files = [tmp_path / f"history-{index}.txt" for index in range(3)]
    for index, path in enumerate(files):
        path.write_text(str(index), encoding="utf-8")
        os.utime(path, (index + 1, index + 1))

    assert prune_old_exports(tmp_path, keep_last=2) == 1
    assert not files[0].exists()
    assert files[1].exists() and files[2].exists()
