"""壁打ちAIブランディングセッション — Streamlit メインアプリ。"""
import os
import uuid
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.persona import PARTS, TOTAL_PARTS
from src.session_manager import SessionManager
from src.summary_generator import generate_branding_sheet
from src.session_store import save as save_session, load as load_session

st.set_page_config(
    page_title="パーソナルブランディングセッション",
    page_icon="✦",
    layout="centered",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { max-width: 720px; }
    .takami-bubble {
        background: #f5f0eb;
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        margin: 4px 0 12px 0;
        line-height: 1.7;
    }
    .user-bubble {
        background: #e8f0fe;
        border-radius: 16px 16px 4px 16px;
        padding: 14px 18px;
        margin: 4px 0 12px 0;
        text-align: right;
        line-height: 1.7;
    }
    .sheet-section {
        background: #fafafa;
        border-left: 4px solid #c9a96e;
        padding: 12px 16px;
        margin: 12px 0;
        border-radius: 0 8px 8px 0;
    }
    .sheet-label {
        font-size: 12px;
        font-weight: bold;
        color: #c9a96e;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .day-complete-box {
        background: #f0faf0;
        border: 2px solid #7bc67e;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# ── セッションID管理 ──────────────────────────────────────────────────────────
def _init_session():
    if "session_id" in st.session_state:
        return

    sid = st.query_params.get("s", None)
    if sid:
        saved = load_session(sid)
        if saved:
            st.session_state.session_id = sid
            st.session_state.screen = saved["screen"]
            st.session_state.messages = saved["messages"]
            st.session_state.sheet = saved["sheet"]
            mgr_data = saved.get("manager")
            st.session_state.manager = SessionManager.from_dict(mgr_data) if mgr_data else None
            return

    new_sid = uuid.uuid4().hex[:12]
    st.session_state.session_id = new_sid
    st.query_params["s"] = new_sid
    st.session_state.screen = "welcome"
    st.session_state.manager = None
    st.session_state.messages = []
    st.session_state.sheet = None


def _persist():
    mgr: SessionManager | None = st.session_state.get("manager")
    save_session(
        session_id=st.session_state.session_id,
        screen=st.session_state.screen,
        messages=st.session_state.messages,
        manager_state=mgr.to_dict() if mgr else None,
        sheet=st.session_state.get("sheet"),
    )


_init_session()


# ── サイドバー：進捗表示 ──────────────────────────────────────────────────────
def _show_sidebar(mgr: SessionManager):
    with st.sidebar:
        completed = mgr.completed_days
        pct = mgr.progress_pct
        st.markdown("#### 進捗状況")
        st.progress(completed / TOTAL_PARTS)
        st.markdown(f"**{pct}% 完了**　DAY {completed} / {TOTAL_PARTS}")
        st.markdown("---")
        for i, part in enumerate(PARTS):
            if i < completed:
                st.markdown(f"✓ DAY {part['id']}　{part['name']}")
            elif i == mgr.part_index and not mgr.finished:
                st.markdown(f"**▶ DAY {part['id']}　{part['name']}**")
            else:
                st.markdown(f"　　DAY {part['id']}　{part['name']}")
        st.markdown("---")
        st.caption("このページをブックマークしておくと、あとで同じ場所から再開できます。")


# ── 画面1：ウェルカム ─────────────────────────────────────────────────────────
def show_welcome():
    st.markdown("## パーソナルブランディングセッション")
    st.markdown("#### あなたらしさを言葉にする、全6DAYの壁打ち体験")
    st.markdown("---")
    st.markdown("""
このセッションでは、**吉田たかみ**があなたの壁打ち相手になります。

チャット形式で質問に答えていくだけで、あなた自身のブランディングの軸が整理されます。

**セッションの流れ（全6DAY）**
""")
    for part in PARTS:
        st.markdown(f"- **DAY {part['id']}**　{part['name']}　—　{part['theme']}")

    st.markdown("""
---
1DAYあたりの目安：**約30分**

答えに正解も不正解もありません。思ったことをそのまま話してください。
""")
    if st.button("DAY 1 を始める", type="primary", use_container_width=True):
        mgr = SessionManager()
        opening = mgr.start()
        st.session_state.manager = mgr
        st.session_state.messages = [{"role": "assistant", "content": opening}]
        st.session_state.screen = "chat"
        _persist()
        st.rerun()


# ── 画面2：チャット ───────────────────────────────────────────────────────────
def show_chat():
    mgr: SessionManager = st.session_state.manager
    _show_sidebar(mgr)

    completed = mgr.completed_days
    current_day = mgr.part_index + 1
    st.markdown(f"##### DAY {current_day} / {TOTAL_PARTS}　{mgr.current_part['name']}")
    st.markdown("---")

    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.markdown(
                f'<div class="takami-bubble">🪴 たかみ<br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="user-bubble">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )

    if not mgr.finished:
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "あなたの答え",
                placeholder="思ったことをそのまま書いてください...",
                height=100,
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("送信", use_container_width=True)

        if submitted and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input.strip()})
            with st.spinner("たかみが考えています..."):
                reply, day_done = mgr.send(user_input.strip())
            st.session_state.messages.append({"role": "assistant", "content": reply})

            if mgr.finished:
                with st.spinner("ブランディングシートを作成しています..."):
                    st.session_state.sheet = generate_branding_sheet(mgr.part_summaries)
                st.session_state.screen = "summary"
            elif day_done:
                st.session_state.screen = "day_complete"

            _persist()
            st.rerun()
    else:
        with st.spinner("ブランディングシートを作成しています..."):
            if not st.session_state.sheet:
                st.session_state.sheet = generate_branding_sheet(mgr.part_summaries)
        st.session_state.screen = "summary"
        _persist()
        st.rerun()


# ── 画面3：DAY完了 ────────────────────────────────────────────────────────────
def show_day_complete():
    mgr: SessionManager = st.session_state.manager
    _show_sidebar(mgr)

    completed = mgr.completed_days
    pct = mgr.progress_pct
    next_day = mgr.part_index + 1

    st.markdown(
        f'<div class="day-complete-box">'
        f'<h2>DAY {completed} 完了！</h2>'
        f'<p>お疲れ様でした！今日はここまでです。</p>'
        f'<p style="font-size:24px; font-weight:bold; color:#2e7d32;">{pct}% 達成</p>'
        f'<p>次は <strong>DAY {next_day}：{PARTS[mgr.part_index]["name"]}</strong> です。</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("**このページをブックマークしておけば、次回ここから再開できます。**")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"続けてDAY {next_day} へ進む", type="primary", use_container_width=True):
            opening = mgr.resume_day()
            st.session_state.messages = [{"role": "assistant", "content": opening}]
            st.session_state.screen = "chat"
            _persist()
            st.rerun()
    with col2:
        if st.button("今日はここで終わる", use_container_width=True):
            st.info("お疲れ様でした！ブックマークしたURLからいつでも再開できます。")


# ── 画面4：サマリー ───────────────────────────────────────────────────────────
def _sheet_to_text(sheet: dict) -> str:
    def section(label, key):
        return [f"【{label}】", sheet.get(key, ""), ""]

    parts = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "　あなたのブランディングシート",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        *section("BRAND CONCEPT / ブランドコンセプト", "brand_concept"),
        *section("TITLE / 肩書き", "title"),
        *section("TECHNICAL SKILLS / テクニカルスキル", "technical_skills"),
        *section("PERSONAL SKILLS / パーソナルスキル", "personal_skills"),
        *section("STORY / なぜあなたが選ばれるか", "story"),
        *section("TARGET CLIENT / ターゲット顧客像", "target_client"),
        *section("GOALS / 目標設定", "goals"),
        *section("30秒自己紹介フレーズ", "intro_phrase"),
        *section("NEXT ACTIONS / 次のアクション", "roadmap"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(parts)


def show_summary():
    sheet = st.session_state.sheet

    st.markdown(
        '<div class="day-complete-box">'
        '<h2>全6DAY 完了！</h2>'
        '<p>素晴らしい！全てのセッションが終わりました。お疲れ様でした！</p>'
        '<p style="font-size:24px; font-weight:bold; color:#2e7d32;">100% 達成</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("## あなたのブランディングシート")
    st.markdown("---")

    sections = [
        ("BRAND CONCEPT", "ブランドコンセプト", sheet.get("brand_concept", "")),
        ("TITLE", "肩書き", sheet.get("title", "")),
        ("TECHNICAL SKILLS", "テクニカルスキル", sheet.get("technical_skills", "")),
        ("PERSONAL SKILLS", "パーソナルスキル", sheet.get("personal_skills", "")),
        ("STORY", "なぜあなたが選ばれるか", sheet.get("story", "")),
        ("TARGET CLIENT", "ターゲット顧客像", sheet.get("target_client", "")),
        ("GOALS", "目標設定", sheet.get("goals", "")),
        ("30秒自己紹介フレーズ", "交流会・SNSで使える自己紹介", sheet.get("intro_phrase", "")),
    ]

    for label_en, label_ja, content in sections:
        if content:
            st.markdown(
                f'<div class="sheet-section">'
                f'<div class="sheet-label">{label_en}</div>'
                f'<strong>{label_ja}</strong><br><br>{content}'
                f'</div>',
                unsafe_allow_html=True,
            )

    if sheet.get("roadmap"):
        st.markdown("---")
        st.markdown(
            f'<div class="sheet-section">'
            f'<div class="sheet-label">NEXT ACTIONS</div>'
            f'<strong>次のアクション</strong><br><br>{sheet["roadmap"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="テキストでダウンロード",
            data=_sheet_to_text(sheet).encode("utf-8"),
            file_name="branding_sheet.txt",
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


# ── ルーティング ──────────────────────────────────────────────────────────────
screen = st.session_state.screen
if screen == "welcome":
    show_welcome()
elif screen == "chat":
    show_chat()
elif screen == "day_complete":
    show_day_complete()
elif screen == "summary":
    show_summary()
