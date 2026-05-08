"""壁打ちAIブランディングセッション — Streamlit メインアプリ。"""
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.persona import PARTS, TOTAL_PARTS
from src.session_manager import SessionManager
from src.summary_generator import generate_branding_sheet

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
    .part-badge {
        font-size: 12px;
        color: #888;
        margin-bottom: 4px;
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
</style>
""", unsafe_allow_html=True)

# ── セッション初期化 ──────────────────────────────────────────────────────────
if "screen" not in st.session_state:
    st.session_state.screen = "welcome"
if "manager" not in st.session_state:
    st.session_state.manager = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sheet" not in st.session_state:
    st.session_state.sheet = None


# ── 画面1：ウェルカム ─────────────────────────────────────────────────────────
def show_welcome():
    st.markdown("## パーソナルブランディングセッション")
    st.markdown("#### あなたらしさを言葉にする、60分の壁打ち体験")
    st.markdown("---")
    st.markdown("""
このセッションでは、**吉田たかみ**があなたの壁打ち相手になります。

チャット形式で質問に答えていくだけで、あなた自身のブランディングの軸が整理されます。

**セッションの流れ（全6パート）**
""")
    for part in PARTS:
        st.markdown(f"- **Part {part['id']}**　{part['name']}　—　{part['theme']}")

    st.markdown("""
---
所要時間の目安：**30〜60分**

答えに正解も不正解もありません。思ったことをそのまま話してください。
""")
    if st.button("セッションを始める", type="primary", use_container_width=True):
        mgr = SessionManager()
        opening = mgr.start()
        st.session_state.manager = mgr
        st.session_state.messages = [{"role": "assistant", "content": opening}]
        st.session_state.screen = "chat"
        st.rerun()


# ── 画面2：チャット ───────────────────────────────────────────────────────────
def show_chat():
    mgr: SessionManager = st.session_state.manager

    # サイドバー：進捗
    with st.sidebar:
        st.markdown("#### セッションの進捗")
        for i, part in enumerate(PARTS):
            if i < mgr.part_index:
                st.markdown(f"✓ Part {part['id']} {part['name']}")
            elif i == mgr.part_index:
                st.markdown(f"**▶ Part {part['id']} {part['name']}**")
            else:
                st.markdown(f"　　Part {part['id']} {part['name']}", unsafe_allow_html=False)
        st.progress(mgr.part_index / TOTAL_PARTS)

    st.markdown(f"##### Part {mgr.part_number} / {TOTAL_PARTS}　{mgr.current_part['name']}")
    st.markdown("---")

    # メッセージ表示
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

    # 入力フォーム
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
                reply, part_done = mgr.send(user_input.strip())
            st.session_state.messages.append({"role": "assistant", "content": reply})

            if mgr.finished:
                with st.spinner("ブランディングシートを作成しています..."):
                    st.session_state.sheet = generate_branding_sheet(mgr.part_summaries)
                st.session_state.screen = "summary"

            st.rerun()
    else:
        # finished フラグが立ったが画面遷移前の保険
        with st.spinner("ブランディングシートを作成しています..."):
            if not st.session_state.sheet:
                st.session_state.sheet = generate_branding_sheet(mgr.part_summaries)
        st.session_state.screen = "summary"
        st.rerun()


# ── 画面3：サマリー ───────────────────────────────────────────────────────────
def _sheet_to_text(sheet: dict) -> str:
    """ブランディングシートをプレーンテキストに変換する。"""
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

    st.markdown("## あなたのブランディングシート")
    st.markdown("セッションお疲れさまでした。あなたのブランディングの軸がまとまりました。")
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
elif screen == "summary":
    show_summary()
