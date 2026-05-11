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
    .celebrate-box {
        background: #f0faf0;
        border: 2px solid #7bc67e;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        text-align: center;
    }
    .day-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 8px 0;
    }
    .day-card-done {
        background: #f0faf0;
        border-color: #7bc67e;
    }
    .day-card-active {
        background: #fff8f0;
        border-color: #c9a96e;
        border-width: 2px;
    }
    .day-card-future {
        background: #fafafa;
        color: #999;
    }
    .url-box {
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: monospace;
        font-size: 13px;
        word-break: break-all;
        margin: 8px 0;
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
            st.session_state.messages = saved["messages"]
            st.session_state.sheet = saved["sheet"]
            mgr_data = saved.get("manager")
            st.session_state.manager = SessionManager.from_dict(mgr_data) if mgr_data else None
            # chatやday_completeから戻ってきた場合はhomeへ
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


# ── 画面2：マイページ（ホーム）───────────────────────────────────────────────
def show_home():
    mgr: SessionManager = st.session_state.manager
    completed = mgr.completed_days
    overall_pct = mgr.overall_progress_pct

    st.markdown("## マイページ")
    st.markdown("---")

    # 全体進捗
    st.markdown("### 全体の進捗")
    st.progress(completed / TOTAL_PARTS)
    st.markdown(f"**{overall_pct}% 完了**　（DAY {completed} / {TOTAL_PARTS} 終了）")
    st.markdown("")

    # DAYカード一覧
    for i, part in enumerate(PARTS):
        if i < completed:
            st.markdown(
                f'<div class="day-card day-card-done">'
                f'✅ <strong>DAY {part["id"]}　{part["name"]}</strong><br>'
                f'<span style="color:#666;font-size:13px;">{part["theme"]} — 完了</span>'
                f'</div>',
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
            # DAYの途中で中断した場合はそのまま会話を再開
            if mgr.day_exchange_count > 0:
                st.session_state.screen = "chat"
            else:
                opening = mgr.resume_day()
                st.session_state.messages = [{"role": "assistant", "content": opening}]
                st.session_state.screen = "chat"
            _persist()
            st.rerun()
    else:
        st.success("全DAY完了！ブランディングシートを確認しましょう。")
        if st.button("ブランディングシートを見る", type="primary", use_container_width=True):
            st.session_state.screen = "summary"
            _persist()
            st.rerun()


# ── 画面3：チャット ───────────────────────────────────────────────────────────
def show_chat():
    mgr: SessionManager = st.session_state.manager
    current_day = mgr.part_index + 1

    # サイドバー
    with st.sidebar:
        if st.button("マイページへ", use_container_width=True):
            st.session_state.screen = "home"
            _persist()
            st.rerun()
        st.markdown("---")
        st.markdown(f"#### DAY {current_day}　{mgr.current_part['name']}")
        st.caption("約30分が目安です。たかみが終了を告げると次のDAYへ進みます。")

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

    st.markdown("---")
    st.markdown(f"**次のセッション：DAY {next_day_num}　{PARTS[mgr.part_index]['name']}**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"続けてDAY {next_day_num} へ進む", type="primary", use_container_width=True):
            opening = mgr.resume_day()
            st.session_state.messages = [{"role": "assistant", "content": opening}]
            st.session_state.screen = "chat"
            _persist()
            st.rerun()
    with col2:
        if st.button("マイページで進捗を確認する", use_container_width=True):
            st.session_state.screen = "home"
            _persist()
            st.rerun()


# ── 画面5：サマリー ───────────────────────────────────────────────────────────
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
        '<div class="celebrate-box">'
        '<h2>全6DAY 完了！おめでとうございます！</h2>'
        '<p style="font-size:18px;">素晴らしい！全てのセッションが終わりました。お疲れ様でした！</p>'
        '<p style="font-size:28px; font-weight:bold; color:#2e7d32;">100% 達成</p>'
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
elif screen == "home":
    show_home()
elif screen == "chat":
    show_chat()
elif screen == "day_complete":
    show_day_complete()
elif screen == "summary":
    show_summary()
