"""セッションデータをSupabaseに保存・復元する。/tmp はフォールバック用。"""
import json
import os
from datetime import datetime
from pathlib import Path

# ── Supabase クライアント初期化 ───────────────────────────────────────────────
def _get_supabase():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
        key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

    if url and key:
        from supabase import create_client
        return create_client(url, key)
    return None


# ── /tmp フォールバック ───────────────────────────────────────────────────────
SESSIONS_DIR = Path("/tmp/branding_sessions")


def _save_file(session_id, data):
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _load_file(session_id) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_all_file() -> list[dict]:
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


# ── 公開API ───────────────────────────────────────────────────────────────────
def save(session_id: str, screen: str, messages: list,
         manager_state: dict | None, sheet: dict | None):
    now = datetime.now().isoformat()
    data = {
        "session_id": session_id,
        "screen": screen,
        "messages": messages,
        "manager": manager_state,
        "sheet": sheet,
        "updated_at": now,
    }

    sb = _get_supabase()
    if sb:
        try:
            # created_at は INSERT 時のみ設定（upsert で既存行があれば上書きしない）
            existing = sb.table("sessions").select("created_at").eq("session_id", session_id).execute()
            if existing.data:
                data["created_at"] = existing.data[0]["created_at"]
            else:
                data["created_at"] = now
            sb.table("sessions").upsert(data).execute()
            return
        except Exception:
            pass  # フォールバックへ

    # /tmp フォールバック
    existing = _load_file(session_id)
    data["created_at"] = existing.get("created_at", now) if existing else now
    _save_file(session_id, data)


def load(session_id: str) -> dict | None:
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table("sessions").select("*").eq("session_id", session_id).execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass

    return _load_file(session_id)


def load_all() -> list[dict]:
    """全セッションを更新日時の降順で返す（管理画面用）。"""
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table("sessions").select("*").order("updated_at", desc=True).execute()
            return result.data or []
        except Exception:
            pass

    return _load_all_file()
