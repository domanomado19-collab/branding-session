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


# ── アクセストークン管理 ──────────────────────────────────────────────────────
TOKENS_FILE = Path("/tmp/branding_tokens.json")


def _tokens_load_file() -> dict:
    if TOKENS_FILE.exists():
        with open(TOKENS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _tokens_save_file(data: dict):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_token(token: str) -> dict | None:
    """トークンを検索して返す。未登録なら None。"""
    token = token.strip().upper()
    sb = _get_supabase()
    if sb:
        try:
            r = sb.table("access_tokens").select("*").eq("token", token).execute()
            return r.data[0] if r.data else None
        except Exception:
            pass
    return _tokens_load_file().get(token)


def consume_token(token: str, session_id: str) -> bool:
    """未使用トークンを使用済みにする。成功で True。"""
    token = token.strip().upper()
    now = datetime.now().isoformat()
    sb = _get_supabase()
    if sb:
        try:
            sb.table("access_tokens").update(
                {"session_id": session_id, "used_at": now}
            ).eq("token", token).is_("used_at", "null").execute()
            return True
        except Exception:
            pass
    tokens = _tokens_load_file()
    if token in tokens and not tokens[token].get("used_at"):
        tokens[token].update({"session_id": session_id, "used_at": now})
        _tokens_save_file(tokens)
        return True
    return False


def create_tokens(count: int = 1, note: str = "") -> list[str]:
    """アクセストークンを生成して保存し、コード一覧を返す。"""
    import secrets
    import string
    chars = string.ascii_uppercase + string.digits

    def _gen() -> str:
        p1 = "".join(secrets.choice(chars) for _ in range(4))
        p2 = "".join(secrets.choice(chars) for _ in range(4))
        return f"MINE-{p1}-{p2}"

    now = datetime.now().isoformat()
    new_tokens = [_gen() for _ in range(count)]

    sb = _get_supabase()
    if sb:
        try:
            rows = [{"token": t, "note": note, "created_at": now} for t in new_tokens]
            sb.table("access_tokens").insert(rows).execute()
            return new_tokens
        except Exception:
            pass
    tokens = _tokens_load_file()
    for t in new_tokens:
        tokens[t] = {"note": note, "created_at": now, "used_at": None, "session_id": None}
    _tokens_save_file(tokens)
    return new_tokens


def list_tokens() -> list[dict]:
    """全トークンを返す（管理画面用）。"""
    sb = _get_supabase()
    if sb:
        try:
            r = sb.table("access_tokens").select("*").order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            pass
    tokens = _tokens_load_file()
    return [{"token": k, **v} for k, v in tokens.items()]


def delete_token(token: str) -> bool:
    """未使用トークンを削除する。"""
    token = token.strip().upper()
    sb = _get_supabase()
    if sb:
        try:
            sb.table("access_tokens").delete().eq("token", token).is_("used_at", "null").execute()
            return True
        except Exception:
            pass
    tokens = _tokens_load_file()
    if token in tokens and not tokens[token].get("used_at"):
        del tokens[token]
        _tokens_save_file(tokens)
        return True
    return False


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
            # on_conflict="session_id" で確実に UPDATE（指定なしだと毎回INSERTになる）
            sb.table("sessions").upsert(data, on_conflict="session_id").execute()
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
            result = (
                sb.table("sessions")
                .select("*")
                .eq("session_id", session_id)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
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
