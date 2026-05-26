"""壁打ちAIブランディングセッション — Streamlit メインアプリ。"""
import os
import uuid
import base64
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as _components
from dotenv import load_dotenv

load_dotenv()

from src.persona import PARTS, TOTAL_PARTS
from src.session_manager import SessionManager
from src.summary_generator import generate_branding_sheet
from src.session_store import save as save_session, load as load_session, load_all as load_all_sessions

st.set_page_config(
    page_title="吉田たかみ｜ブランディングセッション",
    page_icon="✦",
    layout="centered",
)

def _avatar_b64() -> str:
    img_path = Path(__file__).parent / "assets" / "takami.jpg"
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

AVATAR = _avatar_b64()

st.markdown(f"""
<style>
    /* ── 全体 ── */
    .stApp {{ background-color: #faf8f4; }}
    .main {{ max-width: 720px; }}
    h1, h2, h3, h4, h5 {{ color: #2c2c2c; letter-spacing: 0.02em; }}

    /* ── たかみ吹き出し（アバター付き） ── */
    .takami-row {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin: 4px 0 16px 0;
    }}
    .takami-avatar {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 50% 20%;
        flex-shrink: 0;
        border: 2px solid #c9a96e;
        margin-top: 2px;
    }}
    .takami-bubble {{
        background: #f5efe3;
        border-radius: 4px 16px 16px 16px;
        padding: 14px 18px;
        line-height: 1.8;
        color: #2c2c2c;
        font-size: 15px;
        max-width: calc(100% - 56px);
        white-space: pre-line;
    }}
    .takami-name {{
        font-size: 11px;
        color: #c9a96e;
        font-weight: bold;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }}

    /* ── ユーザー吹き出し ── */
    .user-row {{
        display: flex;
        justify-content: flex-end;
        margin: 4px 0 16px 0;
    }}
    .user-bubble {{
        background: #3d3a8c;
        color: #fff;
        border-radius: 16px 4px 16px 16px;
        padding: 14px 18px;
        line-height: 1.8;
        font-size: 15px;
        max-width: 80%;
    }}

    /* ── シート・カード ── */
    .sheet-section {{
        background: #fff;
        border-left: 3px solid #c9a96e;
        padding: 14px 18px;
        margin: 10px 0;
        border-radius: 0 10px 10px 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .sheet-label {{
        font-size: 11px;
        font-weight: bold;
        color: #c9a96e;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
    }}
    .celebrate-box {{
        background: linear-gradient(135deg, #3d3a8c 0%, #5a56b0 100%);
        border-radius: 20px;
        padding: 28px;
        margin: 16px 0;
        text-align: center;
        color: #fff;
    }}
    .celebrate-box h2 {{ color: #fff; }}
    .celebrate-box p {{ color: rgba(255,255,255,0.9); }}
    .day-card {{
        border: 1px solid #e8e0d5;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 8px 0;
        background: #fff;
    }}
    .day-card-done {{
        background: #f5fff5;
        border-color: #7bc67e;
    }}
    .day-card-active {{
        background: #fdf8f0;
        border-color: #c9a96e;
        border-width: 2px;
    }}
    .day-card-future {{
        background: #faf8f4;
        color: #aaa;
    }}

    /* ── サイドバー ── */
    [data-testid="stSidebar"] {{ background-color: #f5f0e8; }}
</style>
""", unsafe_allow_html=True)


# ── セッションID管理 ──────────────────────────────────────────────────────────
USAGE_DAYS = 30  # 利用期限（日数）

def _init_session():
    if "session_id" in st.session_state:
        return

    sid = st.query_params.get("s", None)
    if sid:
        saved = load_session(sid)
        if saved:
            st.session_state.session_id = sid
            st.session_state.messages = saved["messages"]
            st.session_state.sheet = saved["sheet"]
            st.session_state.created_at = saved.get("created_at", datetime.now().isoformat())
            mgr_data = saved.get("manager")
            st.session_state.manager = SessionManager.from_dict(mgr_data) if mgr_data else None
            saved_screen = saved["screen"]
            st.session_state.screen = "home" if saved_screen in ("chat", "day_complete") else saved_screen
            return

    new_sid = uuid.uuid4().hex[:12]
    st.session_state.session_id = new_sid
    st.query_params["s"] = new_sid
    st.session_state.screen = "welcome"
    st.session_state.manager = None
    st.session_state.messages = []
    st.session_state.sheet = None
    st.session_state.created_at = datetime.now().isoformat()


def _remaining_days() -> int:
    """初回アクセスから USAGE_DAYS 日後までの残り日数を返す。"""
    try:
        created = datetime.fromisoformat(st.session_state.get("created_at", datetime.now().isoformat()))
        expiry = created + timedelta(days=USAGE_DAYS)
        return max(0, (expiry - datetime.now()).days)
    except Exception:
        return USAGE_DAYS


def _is_expired() -> bool:
    return _remaining_days() == 0


def _scroll_top():
    _components.html(
        "<script>window.parent.document.querySelector('section.main').scrollTo(0,0);</script>",
        height=0,
    )

def _scroll_bottom():
    _components.html(
        "<script>setTimeout(()=>{const m=window.parent.document.querySelector('section.main');if(m)m.scrollTo(0,m.scrollHeight);},150);</script>",
        height=0,
    )


def _persist():
    mgr: SessionManager | None = st.session_state.get("manager")
    save_session(
        session_id=st.session_state.session_id,
        screen=st.session_state.screen,
        messages=st.session_state.messages,
        manager_state=mgr.to_dict() if mgr else None,
        sheet=st.session_state.get("sheet"),
    )


def _current_url() -> str:
    sid = st.session_state.get("session_id", "")
    try:
        base = st.context.url if hasattr(st, "context") else "https://your-app.streamlit.app"
    except Exception:
        base = "https://your-app.streamlit.app"
    # query_paramsからベースURLを組み立てる
    return f"{base.split('?')[0]}?s={sid}"


_init_session()

WORKSHEETS_DIR = Path(__file__).parent / "assets" / "worksheets"

def _get_worksheet_path(day: int, route: str) -> Path | None:
    p = WORKSHEETS_DIR / f"day{day}.png"
    return p if p.exists() else None

def _show_worksheet(day: int, route: str):
    path = _get_worksheet_path(day, route)
    if path and path.exists():
        st.markdown("---")
        st.markdown(f"**DAY{day} ブランディングノート（空白）**　手書きで記入しながらセッションを進めることができます。")
        st.image(str(path), use_container_width=True)
        with open(path, "rb") as f:
            st.download_button(
                label=f"DAY{day} ブランディングノートをダウンロード",
                data=f.read(),
                file_name=f"branding_note_day{day}.png",
                mime="image/png",
                use_container_width=True,
            )
        st.markdown("---")


# ── DAYまとめ抽出ヘルパー ─────────────────────────────────────────────────────
def _find_summary_message(history: list, day: int) -> str:
    """会話履歴からDAYまとめメッセージを探して返す。"""
    marker = f"【DAY{day}まとめ】"
    for msg in reversed(history):
        if msg["role"] == "assistant" and marker in msg["content"]:
            return msg["content"]
    return ""


def _clean_value(text: str) -> str:
    """マークダウンの ** や * を除去して値を整形する。"""
    import re
    return re.sub(r'\*+', '', text).strip()


def _parse_labeled_lines(text: str, labels: list[str]) -> list[tuple[str, str]]:
    """「ラベル：値」形式の行を順番に抽出して (ラベル, 値) リストで返す。"""
    results = []
    lines = text.split("\n")
    for label in labels:
        for line in lines:
            if label in line and "：" in line:
                raw = line.split("：", 1)[1]
                value = _clean_value(raw)
                if value:
                    results.append((label, value))
                    break
    return results


def _parse_summary_sections(text: str, labels: list[str]) -> list[tuple[str, str]]:
    """まとめテキストから (ラベル, 値) リストを抽出。複数行の値（箇条書き等）にも対応。"""
    import re
    results = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        matched_label = None
        for label in labels:
            if label in line and "：" in line:
                matched_label = label
                break
        if matched_label:
            after_colon = line.split("：", 1)[1].strip()
            value_lines = [after_colon] if after_colon else []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                is_next_label = any(
                    lbl in next_line and "：" in next_line
                    for lbl in labels
                )
                if is_next_label or next_line.startswith("【"):
                    break
                if next_line:
                    value_lines.append(next_line)
                j += 1
            value = re.sub(r'\*+', '', "\n".join(value_lines)).strip()
            if value:
                results.append((matched_label, value))
            i = j
        else:
            i += 1
    return results


def _extract_day_content(history: list, day: int, route: str) -> list[tuple[str, str]]:
    """DAYのまとめから (セクション名, 内容) のリストを返す。"""
    text = _find_summary_message(history, day)
    if not text:
        return []

    if day == 1:
        labels = ["現状のタイプ", "今の働き方", "課題・モヤモヤ"]
    elif day == 2:
        labels = ["理想のタイプ", "実現したい時期", "なぜなりたいか", "そうなれたら嬉しいこと"]
    elif day == 3:
        labels = ["デザインスキルのギャップ", "ブランディングのギャップ", "営業・集客・ビジネス視点のギャップ", "まず取り組むべきこと"]
    else:
        return []

    return _parse_summary_sections(text, labels)


def _day_note_to_text(day: int, route: str, content: list[tuple[str, str]]) -> str:
    """DAYノートをテキスト形式に変換する。"""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  DAY{day} ブランディングノート",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for label, value in content:
        lines += [f"【{label}】", value, ""]
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ── ワークシートサムネイルカード ──────────────────────────────────────────────
def _ws_card(label: str, path: Path, dl_key: str):
    """サムネイル画像＋ダウンロードボタンを1枚のカードとして表示。"""
    if not path.exists():
        return
    st.markdown(
        f'<p style="font-size:12px;font-weight:bold;color:#c9a96e;margin:0 0 4px 0;">{label}</p>',
        unsafe_allow_html=True,
    )
    st.image(str(path), use_container_width=True)
    with open(path, "rb") as f:
        st.download_button(
            label="ダウンロード",
            data=f.read(),
            file_name=path.name,
            mime="image/png",
            use_container_width=True,
            key=dl_key,
        )


def _note_guide_section(route: str = ""):
    """ブランディングノート活用案内（ウェルカム・ホーム共通）。"""
    st.markdown("""
<div style="background:#fdf8f0;border-left:4px solid #c9a96e;padding:16px 20px;
border-radius:0 12px 12px 0;margin:8px 0 16px 0;line-height:1.9;">
<strong>ブランディングノートの使い方</strong><br>
AIとの壁打ちのあとに、自分の言葉でノートにまとめてみると思考がさらに整理されます。<br>
各DAYに対応したワークシートを印刷して、<em>手書きで書き込みながらセッションを進める</em>のがおすすめです。
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    for col, day, label in zip(
        [col1, col2, col3],
        [1, 2, 3],
        ["DAY 1 今の働き方を整理する", "DAY 2 理想の状態を言語化する", "DAY 3 ギャップを整理する"],
    ):
        with col:
            _ws_card(label, WORKSHEETS_DIR / f"day{day}.png", f"dl_day{day}_guide")


# ── 画面1：ウェルカム ─────────────────────────────────────────────────────────
def _load_hero_b64() -> tuple[str, str] | tuple[None, None]:
    """ヒーロー画像をbase64とMIMEタイプで返す。ファイルがなければ(None, None)。"""
    assets = Path(__file__).parent / "assets"
    for fname, mime in [("hero.png", "image/png"), ("hero.jpg", "image/jpeg")]:
        p = assets / fname
        if p.exists():
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode(), mime
    return None, None

HERO_IMG, HERO_MIME = _load_hero_b64()

def show_welcome():
    # ── メインビジュアル ──────────────────────────────────────────────
    if HERO_IMG:
        st.markdown(
            f'<img src="data:{HERO_MIME};base64,{HERO_IMG}" '
            f'style="width:100%;border-radius:12px;display:block;margin-bottom:8px;">',
            unsafe_allow_html=True,
        )
    else:
        # 画像がない場合はテキストヘッダー
        col_img, col_txt = st.columns([1, 2])
        with col_img:
            st.markdown(
                f'<img src="data:image/jpeg;base64,{AVATAR}" '
                f'style="width:120px;height:120px;border-radius:50%;object-fit:cover;'
                f'object-position:50% 20%;border:3px solid #c9a96e;display:block;margin:0 auto;">',
                unsafe_allow_html=True,
            )
        with col_txt:
            st.markdown("### 3days MINE BRANDING")
            st.markdown("*by 吉田たかみ*")
        st.markdown("---")
        st.markdown("""
<div style="background:#fdf8f0;border-left:4px solid #c9a96e;padding:16px 20px;border-radius:0 12px 12px 0;margin:8px 0 20px 0;line-height:1.9;">
「今の自分のままでいいのかな」「どこに向かえばいいのかわからない」——<br>
そんなモヤモヤを持つあなたのための、<strong>3日間のAI壁打ち×ブランディングノート。</strong><br>
現状・理想・ギャップを言語化することで、<em>まず何から始めればいいか</em>が見えてきます。
</div>
""", unsafe_allow_html=True)

    # ── セッションの進め方 ────────────────────────────────────────────
    st.markdown("### セッションの進め方")
    steps = [
        ("DAY 1", "今の働き方を整理する",
         "現在の働き方・課題・モヤモヤを吐き出します。今の自分がどのタイプかを一緒に確認します。"),
        ("DAY 2", "理想の状態を言語化する",
         "なりたい姿・いつ実現したいか・なぜそれを目指したいか・何が嬉しくなるかを言葉にします。"),
        ("DAY 3", "現実と理想のギャップを整理する",
         "デザインスキル・ブランディング・営業集客の3軸でギャップを診断。まず何から始めるかをレコメンドします。"),
    ]
    for i, (day, title, desc) in enumerate(steps):
        arrow = "" if i == len(steps) - 1 else ""
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:14px;margin:10px 0;">'
            f'<div style="background:#1a2d5a;color:#c9a96e;font-weight:bold;font-size:13px;'
            f'padding:6px 12px;border-radius:20px;white-space:nowrap;flex-shrink:0;">{day}</div>'
            f'<div><div style="font-weight:bold;color:#2c2c2c;font-size:15px;">{title}</div>'
            f'<div style="color:#666;font-size:13px;margin-top:3px;">{desc}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if arrow:
            st.markdown('<div style="text-align:center;color:#c9a96e;font-size:18px;margin:-4px 0;">↓</div>',
                        unsafe_allow_html=True)

    st.markdown("""
<div style="background:#f5f0ff;border-radius:12px;padding:12px 16px;margin:12px 0;font-size:13px;color:#5a20a0;line-height:1.8;">
✍ <strong>AIの壁打ち＋手書きノートの組み合わせがおすすめです。</strong><br>
AIとの対話のあと、自分の言葉でノートに書き出してみると、思考がさらに整理されます。<br>
各DAYに対応したワークシートを用意しています。下記からダウンロードして、印刷してご活用ください。
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── ブランディングノートのダウンロード ───────────────────────────
    with st.expander("ブランディングノートをダウンロードする（手書き記入用）"):
        _note_guide_section(route="")

    st.markdown("---")

    # ── スタートボタン＋規約 ──────────────────────────────────────────
    st.markdown("答えに正解も不正解もありません。思ったことをそのまま話してください。")
    st.caption("「DAY 1 をスタートする」を押すことで、利用規約・プライバシーポリシーに同意したものとみなします。")
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        if st.button("利用規約", use_container_width=True):
            st.session_state.legal_from = "welcome"
            st.session_state.screen = "legal"
            st.rerun()
    with col_l2:
        if st.button("プライバシーポリシー", use_container_width=True):
            st.session_state.legal_from = "welcome"
            st.session_state.screen = "legal"
            st.rerun()
    with col_l3:
        if st.button("特定商取引法", use_container_width=True):
            st.session_state.legal_from = "welcome"
            st.session_state.screen = "legal"
            st.rerun()
    st.markdown("---")
    user_name = st.text_input(
        "まず、お名前（呼び名）を教えてください",
        placeholder="例：たかみ、山田さん など",
        max_chars=20,
    )
    if st.button("DAY 1 をスタートする", type="primary", use_container_width=True):
        if not user_name.strip():
            st.warning("お名前を入力してからスタートしてください。")
        else:
            mgr = SessionManager()
            opening = mgr.start(user_name.strip())
            st.session_state.manager = mgr
            st.session_state.messages = [{"role": "assistant", "content": opening}]
            st.session_state.screen = "chat"
            st.session_state.scroll_chat_top = True
            _persist()
            st.rerun()


# ── 画面2：マイページ（ホーム）───────────────────────────────────────────────
def show_home():
    mgr: SessionManager = st.session_state.manager
    completed = mgr.completed_days
    overall_pct = mgr.overall_progress_pct

    if HERO_IMG:
        st.markdown(
            f'<img src="data:{HERO_MIME};base64,{HERO_IMG}" '
            f'style="width:100%;border-radius:12px;display:block;margin-bottom:16px;">',
            unsafe_allow_html=True,
        )
    st.markdown(f"### マイページ")
    st.markdown(f"全体進捗：**{overall_pct}%**　（DAY {completed} / {TOTAL_PARTS} 完了）")
    st.progress(completed / TOTAL_PARTS)
    st.markdown("---")

    # 全体進捗
    st.markdown("### 全体の進捗")
    st.progress(completed / TOTAL_PARTS)
    st.markdown(f"**{overall_pct}% 完了**　（DAY {completed} / {TOTAL_PARTS} 終了）")
    st.markdown("")

    # DAYカード一覧
    for i, part in enumerate(PARTS):
        if i < completed:
            col_card, col_btn = st.columns([4, 1])
            with col_card:
                st.markdown(
                    f'<div class="day-card day-card-done">'
                    f'✅ <strong>DAY {part["id"]}　{part["name"]}</strong><br>'
                    f'<span style="color:#666;font-size:13px;">{part["theme"]} — 完了</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_btn:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                rem = mgr.remaining_restarts(i)
                if rem > 0:
                    if st.button(f"やり直す（残{rem}回）", key=f"restart_{i}", use_container_width=True):
                        opening = mgr.restart_day(i)
                        st.session_state.messages = [{"role": "assistant", "content": opening}]
                        st.session_state.screen = "chat"
                        st.session_state.scroll_chat_top = True
                        _persist()
                        st.rerun()
                else:
                    st.button("やり直し済", key=f"restart_{i}", use_container_width=True, disabled=True)

            # 会話履歴の展開パネル
            day_start = mgr.day_start_indices[i] if i < len(mgr.day_start_indices) else 0
            day_end = mgr.day_start_indices[i + 1] if i + 1 < len(mgr.day_start_indices) else len(mgr.history)
            day_msgs = mgr.history[day_start:day_end]
            if day_msgs:
                with st.expander(f"DAY{i + 1} の会話履歴を見る"):
                    for msg in day_msgs:
                        if msg["role"] == "assistant":
                            st.markdown(
                                f'<div class="takami-row">'
                                f'<img src="data:image/jpeg;base64,{AVATAR}" class="takami-avatar">'
                                f'<div><div class="takami-name">TAKAMI</div>'
                                f'<div class="takami-bubble">{msg["content"]}</div></div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="user-row"><div class="user-bubble">{msg["content"]}</div></div>',
                                unsafe_allow_html=True,
                            )
        elif i == mgr.part_index and not mgr.finished:
            st.markdown(
                f'<div class="day-card day-card-active">'
                f'▶ <strong>DAY {part["id"]}　{part["name"]}</strong>　<span style="color:#c9a96e;">進行中</span><br>'
                f'<span style="color:#666;font-size:13px;">{part["theme"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="day-card day-card-future">'
                f'○ DAY {part["id"]}　{part["name"]}<br>'
                f'<span style="font-size:13px;">{part["theme"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    if not mgr.finished:
        next_day_num = mgr.part_index + 1
        if st.button(f"DAY {next_day_num} を続ける", type="primary", use_container_width=True):
            if st.session_state.messages:
                # 途中から再開→続きから表示（スクロールフラグなし）
                st.session_state.screen = "chat"
            else:
                opening = mgr.resume_day()
                st.session_state.messages = [{"role": "assistant", "content": opening}]
                st.session_state.screen = "chat"
                st.session_state.scroll_chat_top = True  # 新DAY開始→上部から
            _persist()
            st.rerun()
    else:
        st.success("全DAY完了！あなたのブランディングノートを確認しましょう。")
        if st.button("ブランディングノートを見る", type="primary", use_container_width=True):
            st.session_state.screen = "summary"
            _persist()
            st.rerun()

    # ── ブランディングノートダウンロード ──────────────────────────────
    st.markdown("---")
    with st.expander("ワークシートをダウンロードする（手書き記入用）"):
        st.markdown("""
AIとの壁打ちのあとに、自分の言葉でノートに書き出してみると思考がさらに整理されます。
各DAYに対応したワークシートを印刷して、手書きで記入しながらセッションを進めるのもおすすめです。
""")
        _note_guide_section(route=mgr.route)


# ── 画面3：チャット ───────────────────────────────────────────────────────────
def show_chat():
    mgr: SessionManager = st.session_state.manager
    current_day = mgr.part_index + 1
    completed_day = mgr.completed_days  # DAY完了数（完了直後はこちらを表示）

    # ── スクロール制御 ────────────────────────────────────────────────
    if st.session_state.pop("scroll_chat_top", False):
        _scroll_top()
    elif st.session_state.pop("scroll_chat_bottom", False):
        _scroll_bottom()

    # サイドバー
    remaining = _remaining_days()
    with st.sidebar:
        if st.button("マイページへ", use_container_width=True):
            st.session_state.screen = "home"
            _persist()
            st.rerun()
        st.markdown("---")
        if mgr.day_just_completed:
            st.markdown(f"#### DAY {completed_day} 完了！")
            st.caption("下のボタンからブランディングノートを確認できます。")
        else:
            st.markdown(f"#### DAY {current_day} / {TOTAL_PARTS}")
            st.markdown(f"**{mgr.current_part['name']}**")
        st.markdown("---")
        st.markdown(f"**進捗** {mgr.overall_progress_pct}%")
        st.progress(mgr.overall_progress_pct / 100)
        _type_name = {"side_job": "副業スタート型", "inhouse": "業務委託型",
                      "specialist": "起業家型", "business_owner": "ディレクター型"}
        if mgr.route:
            st.markdown(
                f'<div style="background:#fdf8f0;border-radius:8px;padding:8px 12px;'
                f'margin:8px 0;font-size:13px;">'
                f'<span style="color:#c9a96e;font-size:10px;font-weight:bold;letter-spacing:.08em;">現状タイプ</span><br>'
                f'<strong>{_type_name.get(mgr.route, mgr.route)}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if remaining > 5:
            st.caption(f"利用期限まで あと **{remaining}日**")
        elif remaining > 0:
            st.warning(f"利用期限まで あと **{remaining}日**")
        else:
            st.error("利用期限が終了しています")

    if mgr.day_just_completed:
        st.markdown(f"##### DAY {completed_day} 完了！")
    else:
        st.markdown(f"##### DAY {current_day} / {TOTAL_PARTS}　{mgr.current_part['name']}")

    # DAY開始時にワークシートを表示（最初のメッセージが1件のみ＝開始直後）
    if len(st.session_state.messages) == 1 and not mgr.day_just_completed:
        _show_worksheet(current_day, mgr.route)

    st.markdown("---")

    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.markdown(
                f'<div class="takami-row">'
                f'<img src="data:image/jpeg;base64,{AVATAR}" class="takami-avatar">'
                f'<div><div class="takami-name">TAKAMI</div>'
                f'<div class="takami-bubble">{msg["content"]}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="user-row"><div class="user-bubble">{msg["content"]}</div></div>',
                unsafe_allow_html=True,
            )

    if mgr.day_just_completed:
        # DAY完了後：ブランディングノートへのボタンを表示
        st.markdown("---")
        if mgr.finished:
            btn_label = "3DAYSまとめノートを見る"
        else:
            btn_label = f"DAY{completed_day} ブランディングノートを見る"
        if st.button(btn_label, type="primary", use_container_width=True):
            if mgr.finished:
                with st.spinner("ブランディングシートを作成しています..."):
                    st.session_state.sheet = generate_branding_sheet(mgr.part_summaries)
                st.session_state.screen = "summary"
            else:
                st.session_state.screen = "day_complete"
            _persist()
            st.rerun()
    elif not mgr.finished:
        # 下部固定チャット入力
        user_input = st.chat_input("思ったことをそのまま書いてください...（Enterで送信）")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            try:
                with st.spinner("たかみが考えています..."):
                    reply, day_done = mgr.send(user_input)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                if mgr.day_just_completed:
                    st.session_state.scroll_chat_bottom = True  # DAY完了→ボタンが見える位置へ
                _persist()
                st.rerun()
            except RuntimeError as e:
                st.session_state.messages.pop()  # 追加したuserメッセージを戻す
                err = str(e)
                if err == "rate_limit":
                    st.warning(
                        "リクエストが集中しています。少し時間をおいてから再度送信してください。\n\n"
                        "（しばらく待ってもエラーが続く場合はLINEよりご連絡ください）"
                    )
                elif err == "auth_error":
                    st.error(
                        "APIキーの認証に失敗しました。\n\n"
                        "管理者にご連絡ください。"
                    )
                elif err == "overloaded":
                    st.warning(
                        "AIサーバーが混雑しています。1〜2分後にもう一度お試しください。"
                    )
                else:
                    st.error(
                        "送信中にエラーが発生しました。しばらく待ってから再度お試しください。\n\n"
                        "問題が続く場合はLINEよりご連絡ください。"
                    )
            except Exception as e:
                st.session_state.messages.pop()
                st.error(
                    "予期しないエラーが発生しました。ページを再読み込みしてお試しください。"
                )


# ── 画面4：DAY完了 ────────────────────────────────────────────────────────────
def show_day_complete():
    mgr: SessionManager = st.session_state.manager
    completed = mgr.completed_days
    overall_pct = mgr.overall_progress_pct
    next_day_num = mgr.part_index + 1

    st.markdown(
        f'<div class="celebrate-box">'
        f'<h2>DAY {completed} 完了！</h2>'
        f'<p style="font-size:18px;">お疲れ様でした！今日はここまでです。</p>'
        f'<p style="font-size:28px; font-weight:bold; color:#2e7d32;">{overall_pct}% 達成</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # 再開方法の案内
    st.markdown("### 次回の再開方法")
    st.info(
        "**このページのURLをブックマーク**しておくと、次回同じ場所から再開できます。\n\n"
        "📱 スマホの場合：ブラウザの「共有」→「ブックマークに追加」\n\n"
        "💻 PCの場合：Cmd+D（Mac）/ Ctrl+D（Windows）でブックマーク"
    )
    st.markdown(f"次回はこのURLを開くだけで再開できます：")
    st.code(f"?s={st.session_state.session_id}", language=None)
    st.caption("※ URLが変わった場合は上のID部分（?s=〜）を保存しておいてください。")

    # ── DAYブランディングノート（テキスト形式） ────────────────────────
    st.markdown("---")
    st.markdown(f"### DAY {completed} ブランディングノート")

    day_content = _extract_day_content(mgr.history, completed, mgr.route)
    # 値が空のフィールドを除外
    day_content_clean = [(lbl, val) for lbl, val in day_content if val]

    if day_content_clean:
        for label, value in day_content_clean:
            st.markdown(
                f'<div class="sheet-section">'
                f'<div class="sheet-label">{label}</div>'
                f'{value}'
                f'</div>',
                unsafe_allow_html=True,
            )
        # 抽出できなかったフィールドがある場合は振り返り全文も補足表示
        if len(day_content_clean) < len(day_content):
            recap = _find_summary_message(mgr.history, completed)
            if recap:
                with st.expander("振り返り全文を見る"):
                    st.markdown(recap)
    else:
        # パース完全失敗時→振り返り全文をそのまま表示
        recap = _find_summary_message(mgr.history, completed)
        if recap:
            st.markdown(recap)
        else:
            st.markdown(mgr.part_summaries[-1] if mgr.part_summaries else "")

    note_txt = _day_note_to_text(completed, mgr.route, day_content_clean)
    st.download_button(
        label=f"DAY{completed} ブランディングノートをテキストでダウンロード",
        data=note_txt.encode("utf-8"),
        file_name=f"branding_note_day{completed}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # 空白ワークシート（手書き用）
    _show_worksheet(completed, mgr.route)

    # DAY3完了時はLINEボタンを表示
    if mgr.finished:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#3d3a8c,#5a56b0);border-radius:16px;'
            'padding:24px;text-align:center;margin:16px 0;">'
            '<p style="color:#fff;font-size:16px;margin-bottom:8px;">'
            '見えてきたギャップを、一緒に埋めていきませんか？</p>'
            '<p style="color:rgba(255,255,255,0.8);font-size:14px;margin-bottom:16px;">'
            'デザインスキル・ブランディング・集客など、個別相談でサポートします。</p>'
            '<a href="https://lin.ee/yZCe0OW" target="_blank" style="'
            'display:inline-block;background:#06C755;color:#fff;font-weight:bold;'
            'font-size:18px;padding:14px 40px;border-radius:50px;text-decoration:none;">'
            'LINEで個別相談に申し込む</a>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if not mgr.finished:
        st.markdown(f"**次のセッション：DAY {next_day_num}　{PARTS[mgr.part_index]['name']}**")
    st.markdown("このまま続けますか？それとも今日はここで終わりにしますか？")

    col1, col2 = st.columns(2)
    with col1:
        if mgr.finished:
            if st.button("ブランディングノートを見る", type="primary", use_container_width=True):
                st.session_state.screen = "summary"
                _persist()
                st.rerun()
        elif st.button(f"このまま続ける（DAY {next_day_num} へ）", type="primary", use_container_width=True):
            opening = mgr.resume_day()
            st.session_state.messages = [{"role": "assistant", "content": opening}]
            st.session_state.screen = "chat"
            _persist()
            st.rerun()
    with col2:
        if st.button("マイページに戻る", use_container_width=True):
            st.session_state.screen = "home"
            _persist()
            st.rerun()


# ── 画面5：サマリー ───────────────────────────────────────────────────────────
def _sheet_to_text(sheet: dict) -> str:
    def section(label, key):
        return [f"【{label}】", sheet.get(key, ""), ""]

    parts = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "　3DAYS MINE BRANDING ノート",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "▼ DAY1：現状",
        *section("現状のタイプ", "current_type"),
        *section("今の働き方", "current_situation"),
        *section("課題・モヤモヤ", "current_struggles"),
        "▼ DAY2：理想",
        *section("理想のタイプ", "ideal_type"),
        *section("実現したい時期", "ideal_timeline"),
        *section("なぜなりたいか", "ideal_reason"),
        *section("そうなれたら嬉しいこと", "ideal_benefits"),
        "▼ DAY3：ギャップ診断",
        *section("デザインスキルのギャップ", "design_skill_gaps"),
        *section("ブランディングのギャップ", "branding_gaps"),
        *section("営業・集客・ビジネス視点のギャップ", "business_gaps"),
        *section("まず取り組むべきこと", "priority_actions"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "現状と理想のギャップが見えたら、まず一歩踏み出しましょう。",
    ]
    return "\n".join(parts)


def show_summary():
    sheet = st.session_state.sheet

    st.markdown(
        '<div class="celebrate-box">'
        '<h2>3DAYS 完了！おめでとうございます！</h2>'
        '<p style="font-size:18px;">素晴らしい！全てのセッションが終わりました。お疲れ様でした！</p>'
        '<p style="font-size:28px; font-weight:bold; color:#fff;">100% 達成</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("## あなたのブランディングノート")
    st.markdown("---")

    st.markdown("### DAY1：現状")
    day1_sections = [
        ("CURRENT TYPE", "現状のタイプ", sheet.get("current_type", "")),
        ("NOW", "今の働き方", sheet.get("current_situation", "")),
        ("STRUGGLES", "課題・モヤモヤ", sheet.get("current_struggles", "")),
    ]
    for label_en, label_ja, content in day1_sections:
        if content:
            st.markdown(
                f'<div class="sheet-section">'
                f'<div class="sheet-label">{label_en}</div>'
                f'<strong>{label_ja}</strong><br><br>{content}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("### DAY2：理想")
    day2_sections = [
        ("IDEAL TYPE", "理想のタイプ", sheet.get("ideal_type", "")),
        ("TIMELINE", "実現したい時期", sheet.get("ideal_timeline", "")),
        ("WHY", "なぜなりたいか", sheet.get("ideal_reason", "")),
        ("BENEFITS", "そうなれたら嬉しいこと", sheet.get("ideal_benefits", "")),
    ]
    for label_en, label_ja, content in day2_sections:
        if content:
            st.markdown(
                f'<div class="sheet-section">'
                f'<div class="sheet-label">{label_en}</div>'
                f'<strong>{label_ja}</strong><br><br>{content}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("### DAY3：ギャップ診断")
    day3_sections = [
        ("DESIGN SKILL", "デザインスキルのギャップ", sheet.get("design_skill_gaps", "")),
        ("BRANDING", "ブランディングのギャップ", sheet.get("branding_gaps", "")),
        ("BUSINESS", "営業・集客・ビジネス視点のギャップ", sheet.get("business_gaps", "")),
        ("PRIORITY", "まず取り組むべきこと", sheet.get("priority_actions", "")),
    ]
    for label_en, label_ja, content in day3_sections:
        if content:
            st.markdown(
                f'<div class="sheet-section">'
                f'<div class="sheet-label">{label_en}</div>'
                f'<strong>{label_ja}</strong><br><br>{content}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── LINEコンバージョンボタン ─────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="background:linear-gradient(135deg,#3d3a8c,#5a56b0);border-radius:16px;'
        'padding:24px;text-align:center;margin:16px 0;">'
        '<p style="color:#fff;font-size:16px;margin-bottom:8px;">'
        '見えてきたギャップを、一緒に埋めていきませんか？</p>'
        '<p style="color:rgba(255,255,255,0.8);font-size:14px;margin-bottom:16px;">'
        'デザインスキル・ブランディング・集客など、個別相談でサポートします。</p>'
        '<a href="https://lin.ee/yZCe0OW" target="_blank" style="'
        'display:inline-block;background:#06C755;color:#fff;font-weight:bold;'
        'font-size:18px;padding:14px 40px;border-radius:50px;text-decoration:none;">'
        'LINEで個別相談に申し込む</a>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    if st.button("マイページに戻る（振り返り・会話履歴）", use_container_width=True):
        st.session_state.screen = "home"
        _persist()
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="テキストでダウンロード",
            data=_sheet_to_text(sheet).encode("utf-8"),
            file_name="branding_note.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        if st.button("もう一度セッションをやり直す", use_container_width=True):
            new_sid = uuid.uuid4().hex[:12]
            st.session_state.session_id = new_sid
            st.query_params["s"] = new_sid
            st.session_state.screen = "welcome"
            st.session_state.manager = None
            st.session_state.messages = []
            st.session_state.sheet = None
            st.rerun()

    st.caption("ブラウザの印刷メニュー（Cmd+P / Ctrl+P）→「PDFに保存」でPDF化できます。")


# ── 画面6：管理ダッシュボード ────────────────────────────────────────────────
ROUTE_LABEL = {
    "side_job": "副業スタート型",
    "inhouse": "業務委託型",
    "specialist": "起業家型",
    "business_owner": "ディレクター型",
}

def _admin_password() -> str:
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return os.environ.get("ADMIN_PASSWORD", "takami2024")


def show_admin():
    st.markdown("## 管理ダッシュボード")

    # ── パスワード認証 ────────────────────────────────────────────────
    if not st.session_state.get("admin_authed"):
        pw = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン", type="primary"):
            if pw == _admin_password():
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return

    if st.button("ログアウト", use_container_width=False):
        st.session_state.admin_authed = False
        st.rerun()

    # ── Supabase 接続確認 ─────────────────────────────────────────────
    from src.session_store import _get_supabase
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table("sessions").select("session_id", count="exact").execute()
            st.success(f"Supabase 接続OK　{result.count or 0} 件のセッション")
        except Exception as e:
            st.error(f"Supabase エラー: {e}")
            sb = None
    else:
        st.warning("Supabase 未接続（/tmp を使用中）　— Secrets を確認してください")

    sessions = load_all_sessions()
    if not sessions:
        st.info("セッションデータがまだありません。")
        return

    # ── 集計 ──────────────────────────────────────────────────────────
    total = len(sessions)
    def completed_days(s):
        return len((s.get("manager") or {}).get("part_summaries") or [])

    cnt = {0: 0, 1: 0, 2: 0, 3: 0}
    for s in sessions:
        cnt[min(completed_days(s), 3)] += 1

    route_cnt: dict[str, int] = {}
    for s in sessions:
        r = (s.get("manager") or {}).get("route", "")
        if r:
            route_cnt[r] = route_cnt.get(r, 0) + 1

    # ── 概要カード ────────────────────────────────────────────────────
    st.markdown("### 概要")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("総セッション数", total)
    c2.metric("開始のみ", cnt[0])
    c3.metric("DAY1完了", cnt[1])
    c4.metric("DAY2完了", cnt[2])
    c5.metric("DAY3全完了", cnt[3])

    if total > 0:
        st.progress(cnt[3] / total, text=f"全完了率 {cnt[3]/total:.0%}")

    # ルート分布
    if route_cnt:
        st.markdown("**ルート分布（DAY1完了以上）**")
        cols = st.columns(len(route_cnt))
        for col, (route, count) in zip(cols, route_cnt.items()):
            col.metric(ROUTE_LABEL.get(route, route), count)

    st.markdown("---")

    # ── フィルター ────────────────────────────────────────────────────
    st.markdown("### ユーザー一覧")
    filter_opt = st.radio(
        "表示フィルター",
        ["全員", "開始のみ", "DAY1完了", "DAY2完了", "DAY3全完了"],
        horizontal=True,
    )
    filter_map = {"全員": None, "開始のみ": 0, "DAY1完了": 1, "DAY2完了": 2, "DAY3全完了": 3}
    filter_val = filter_map[filter_opt]

    shown = [s for s in sessions if filter_val is None or completed_days(s) == filter_val]

    if not shown:
        st.info("該当するセッションがありません。")
        return

    # ── ユーザーカード ─────────────────────────────────────────────────
    day_names = ["（開始のみ）", "DAY1完了", "DAY2完了", "DAY3全完了"]
    progress_pct = [0, 33, 66, 100]

    for s in shown:
        mgr = s.get("manager") or {}
        sid = s["session_id"]
        n_done = completed_days(s)
        route = mgr.get("route", "")
        finished = mgr.get("finished", False)
        updated = s.get("updated_at", "")[:16].replace("T", " ")
        created = s.get("created_at", "")[:16].replace("T", " ")
        summaries: list[str] = mgr.get("part_summaries") or []
        sheet: dict = s.get("sheet") or {}

        label = "✅ 全完了" if finished else f"▶ {day_names[n_done]}"
        route_str = ROUTE_LABEL.get(route, "（未判定）") if route else "（未判定）"

        with st.expander(f"**{sid[:8]}…** — {label}　{route_str}　最終アクセス: {updated}"):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**進捗** {progress_pct[n_done]}%")
            col_b.markdown(f"**ルート** {route_str}")
            col_c.markdown(f"**開始日** {created}")
            st.progress(progress_pct[n_done] / 100)

            # DAYごとのサマリー
            for day_i, summary in enumerate(summaries, start=1):
                st.markdown(f"**DAY{day_i} まとめ**")
                st.markdown(
                    f'<div class="sheet-section" style="margin:4px 0;">'
                    f'<div style="font-size:13px;color:#555;white-space:pre-line;">{summary}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # DAY3完了時はブランディングシートも表示
            if finished and sheet:
                st.markdown("**ブランディングシート**")
                sheet_labels = [
                    ("現状のタイプ", "current_type"),
                    ("今の働き方", "current_situation"),
                    ("課題・モヤモヤ", "current_struggles"),
                    ("理想のタイプ", "ideal_type"),
                    ("実現したい時期", "ideal_timeline"),
                    ("なぜなりたいか", "ideal_reason"),
                    ("そうなれたら嬉しいこと", "ideal_benefits"),
                    ("デザインスキルのギャップ", "design_skill_gaps"),
                    ("ブランディングのギャップ", "branding_gaps"),
                    ("営業・集客・ビジネス視点のギャップ", "business_gaps"),
                    ("まず取り組むべきこと", "priority_actions"),
                ]
                for label_ja, key in sheet_labels:
                    val = sheet.get(key, "")
                    if val:
                        st.markdown(
                            f'<div class="sheet-section" style="margin:4px 0;">'
                            f'<div class="sheet-label">{label_ja}</div>'
                            f'{val}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )


# ── 利用期限切れ画面 ──────────────────────────────────────────────────────────
def show_expired():
    st.markdown(
        '<div class="celebrate-box" style="background:linear-gradient(135deg,#666,#999);">'
        '<h2 style="color:#fff;">ご利用期限が終了しました</h2>'
        '<p style="color:rgba(255,255,255,0.9);">3days MINE BRANDING の利用期限（30日間）が終了しました。</p>'
        '<p style="color:rgba(255,255,255,0.9);">引き続き個別相談でサポートします。</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="text-align:center;margin-top:24px;">'
        '<a href="https://lin.ee/yZCe0OW" target="_blank" style="'
        'display:inline-block;background:#06C755;color:#fff;font-weight:bold;'
        'font-size:18px;padding:14px 40px;border-radius:50px;text-decoration:none;">'
        'LINEで個別相談に申し込む</a>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── 法律ページ ─────────────────────────────────────────────────────────────────
def show_legal():
    st.markdown("## 各種規約・表記")
    tab1, tab2, tab3 = st.tabs(["利用規約", "プライバシーポリシー", "特定商取引法に基づく表記"])

    with tab1:
        st.markdown("""
### 3days MINE BRANDING 利用規約
制定日：2026年5月14日

**第1条　適用**
本規約は、3days MINE BRANDING（以下「本サービス」）の利用条件を定めるものです。本サービスを購入または利用する方（以下「利用者」）は、本規約に同意のうえご利用ください。

**第2条　サービス内容**
本サービスは、AIとの対話・ブランディングノート・ワークシートを通じて、利用者の働き方・経験・強み・方向性を整理し、肩書き・自己紹介・プロフィール文等の仮説作成を支援するセルフブランディングサービスです。特定の成果を保証するものではありません。

**第3条　成果保証の否認**
運営者は、売上増加・案件獲得・単価アップ・集客成果・独立副業成功等の特定の成果を保証しません。利用者は本サービスで得られた内容を参考情報として利用し、最終的な判断・行動を自己の責任において行うものとします。

**第4条　AI出力に関する注意**
AI による回答には不正確・不完全・不適切な内容が含まれる場合があります。運営者はAI出力の正確性・完全性・有用性・適法性・独自性・第三者権利非侵害性を保証しません。

**第5条　入力情報に関する注意**
以下の情報を入力しないでください：①第三者の個人情報　②クライアント・勤務先等の機密情報　③未公開案件・秘密保持義務のある情報　④他者著作物の無断複製　⑤誹謗中傷・差別・違法行為に関する情報。これらの入力により生じた損害について運営者は責任を負いません。

**第6条　個人情報および入力内容の取り扱い**
取得した情報はサービス提供・AI回答生成・問い合わせ対応・サービス改善・関連サービス案内・法令対応に利用します。詳細は別途プライバシーポリシーをご確認ください。

**第7条　知的財産権**
本サービスに含まれる教材・ワークシート・プロンプト・デザイン等の権利は運営者または正当な権利者に帰属します。運営者の許可なく複製・転載・配布・販売・講座化・二次利用することはできません。

**第8条　生成物の利用**
本サービスで生成された肩書き・自己紹介文・プロフィール文等は自身の活動に利用できます。ただし独自性・商標登録可能性・第三者権利非侵害・法令適合性を保証しません。

**第9条　禁止事項**
①本サービス内容の無断複製・転載・販売・配布　②類似サービス・講座・教材の無断作成・販売　③他者の権利侵害　④虚偽情報の入力　⑤サービス運営の妨害　⑥法令・公序良俗に反する行為

**第10条　料金・支払い**
利用者は運営者が定める料金を指定の方法で支払うものとします。

**第11条　キャンセル・返金**
本サービスはデジタルコンテンツおよびAI壁打ちサービスの性質上、購入後のキャンセル・返金は原則お受けしておりません。ただし運営者の責に帰すべきシステム不具合により利用できない場合は個別に対応します。

**第12条　サービスの変更・停止**
運営者は必要に応じてサービスの内容・仕様・提供方法を変更・停止・終了することがあります。

**第13条　免責事項**
運営者は本サービスの利用または利用不能により生じた損害について、故意または重過失がある場合を除き責任を負いません。

**第14条　規約の変更**
運営者は必要に応じて本規約を変更することがあります。変更後の規約は運営者が指定する方法により周知した時点で効力を生じます。

**第15条　準拠法・管轄**
本規約は日本法に準拠します。紛争が生じた場合、運営者の所在地を管轄する裁判所を第一審の専属的合意管轄裁判所とします。
""")

    with tab2:
        st.markdown("""
### プライバシーポリシー
制定日：2026年5月14日

**第1条　基本方針**
株式会社ドマノマドは、3days MINE BRANDINGの提供にあたり、利用者の個人情報および入力情報を適切に取り扱うため、本プライバシーポリシーを定めます。

**第2条　取得する情報**
・氏名・メールアドレス等の連絡先情報　・AIセッション・ワークシートに入力された内容　・問い合わせ・個別相談申込みで送信された内容　・Cookie・アクセスログ等の利用状況情報

**第3条　利用目的**
・本サービスの提供・本人確認・決済・利用案内　・AI回答生成・ワーク結果の作成・セッション履歴確認　・問い合わせ対応・重要なお知らせの送付　・個別相談・関連サービス・キャンペーンの案内　・サービス改善・品質向上・利用状況分析　・不正利用・規約違反等への対応　・法令または行政機関等からの要請への対応

**第4条　AIおよび外部サービスの利用**
AI回答生成等のため外部サービスを利用する場合があります。サービス提供に必要な範囲で入力内容が外部サービスに送信・処理されることがあります。クライアント名・勤務先の機密情報・第三者の個人情報等は入力しないでください。

**第5条　第三者提供**
法令に基づく場合・利用者の同意がある場合・業務委託先への必要範囲での提供を除き、個人情報を第三者に提供しません。

**第6条　安全管理**
情報の漏えい・滅失・毀損・不正アクセス等を防止するため、必要かつ適切な安全管理措置を講じます。

**第7条　Cookie等の利用**
サイトの利便性向上・利用状況分析等のためCookie等を使用する場合があります。

**第8条　開示・訂正・削除等の請求**
利用者は保有する自己の個人情報について開示・訂正・削除・利用停止等を求めることができます。

**第9条　プライバシーポリシーの変更**
必要に応じて本ポリシーを変更することがあります。

**第10条　お問い合わせ窓口**
事業者名：株式会社ドマノマド　運営責任者：吉田たかみ
""")

    with tab3:
        st.markdown("""
### 特定商取引法に基づく表記

| 項目 | 内容 |
|---|---|
| 販売事業者 | 株式会社ドマノマド |
| 運営責任者 | 吉田たかみ |
| 所在地 | 公開前に正式な所在地を記載 |
| 電話番号 | 公開前に記載 |
| メールアドレス | 公開前に問い合わせ先を記載 |
| 販売価格 | 3days MINE BRANDING：9,800円（税込） |
| 商品代金以外の費用 | インターネット接続料金・通信料等は利用者負担 |
| 支払方法 | クレジットカード決済・銀行振込・その他指定の方法 |
| サービス提供時期 | 決済完了後、利用案内を送付し提供開始 |
| キャンセル・返金 | デジタルコンテンツの性質上、購入後のキャンセル・返金は原則不可。システム不具合の場合は個別対応 |
| 動作環境 | インターネット接続可能なスマートフォン・タブレット・PC＋Webブラウザ |

**成果に関する注意**：本サービスは自己理解・方向性整理・肩書き仮説の作成を支援するものです。売上増加・案件獲得・集客成果等を保証するものではありません。
""")

    st.markdown("---")
    if st.button("← 戻る", use_container_width=False):
        st.session_state.screen = st.session_state.get("legal_from", "welcome")
        st.rerun()


# ── ルーティング ──────────────────────────────────────────────────────────────
if st.query_params.get("page") == "admin":
    show_admin()
else:
    _init_session()

    # 利用期限チェック（welcomeと法律ページは除く）
    screen = st.session_state.screen
    if screen not in ("welcome", "legal") and _is_expired():
        show_expired()
    elif st.query_params.get("page") == "legal":
        show_legal()
    elif screen == "welcome":
        show_welcome()
    elif screen == "home":
        show_home()
    elif screen == "chat":
        show_chat()
    elif screen == "day_complete":
        show_day_complete()
    elif screen == "summary":
        show_summary()
    elif screen == "legal":
        show_legal()
