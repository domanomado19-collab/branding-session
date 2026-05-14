"""セッションデータをファイルに保存・復元する。"""
import json
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path("/tmp/branding_sessions")


def save(session_id: str, screen: str, messages: list, manager_state: dict | None, sheet: dict | None):
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"

    # 既存データから created_at を引き継ぐ
    created_at = datetime.now().isoformat()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            created_at = existing.get("created_at", created_at)
        except Exception:
            pass

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "screen": screen,
                "messages": messages,
                "manager": manager_state,
                "sheet": sheet,
                "created_at": created_at,
                "updated_at": datetime.now().isoformat(),
            },
            f,
            ensure_ascii=False,
        )


def load(session_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_all() -> list[dict]:
    """全セッションを更新日時の降順で返す（管理画面用）。"""
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["session_id"] = path.stem
            sessions.append(data)
        except Exception:
            continue
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions
