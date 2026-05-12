"""セッションデータをファイルに保存・復元する。"""
import json
from pathlib import Path

SESSIONS_DIR = Path("/tmp/branding_sessions")


def save(session_id: str, screen: str, messages: list, manager_state: dict | None, sheet: dict | None):
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"screen": screen, "messages": messages, "manager": manager_state, "sheet": sheet},
            f,
            ensure_ascii=False,
        )


def load(session_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None
