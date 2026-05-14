"""壁打ちAIブランディングセッション — Streamlit メインアプリ。"""
import os
import uuid
import base64
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.persona import PARTS, TOTAL_PARTS
from src.session_manager import SessionManager
from src.summary_generator import generate_branding_sheet
from src.session_store import save as save_session, load as load_session
from src.note_generator import generate_note_image

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
        object-position: top;
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

WORKSHEETS_DIR = Path(__file__).parent / "assets" / "worksheets"

def _get_worksheet_path(day: int, route: str) -> Path | None:
    if day == 1:
        return WORKSHEETS_DIR / "day1.png"
    route_key = route if route in ("side_job", "inhouse", "specialist") else "specialist"
    path = WORKSHEETS_DIR / f"day{day}_{route_key}.png"
    return path if path.exists() else None

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


# ── 画面1：ウェルカム ─────────────────────────────────────────────────────────
def show_welcome():
    # ヘッダー：写真＋タイトル
    col_img, col_txt = st.columns([1, 2])
    with col_img:
        st.markdown(
            f'<img src="data:image/jpeg;base64,{AVATAR}" '
            f'style="width:120px;height:120px;border-radius:50%;object-fit:cover;'
            f'object-position:top;border:3px solid #c9a96e;display:block;margin:0 auto;">',
            unsafe_allow_html=True,
        )
    with col_txt:
        st.markdown("### 吉田たかみの\nブランディングセッション")
        st.markdown("*選ばれる肩書きをつくる、3DAYSセルフブランディングノート*")
    st.markdown("---")
    st.markdown("""
このセッションでは、**吉田たかみ**があなたの壁打ち相手になります。

チャット形式で質問に答えていくだけで、あなた自身のブランディングの軸が整理されます。

**セッションの流れ（全3DAYS）**
""")
    for part in PARTS:
        st.markdown(f"- **DAY {part['id']}**　{part['name']}　—　{part['theme']}")

    st.markdown("---")
    st.markdown("#### デザイナーの働き方タイプ（DAY1で確認します）")
    st.markdown("""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0 16px 0;">
  <div style="background:#f0f0ff; border-radius:12px; padding:14px; border:1px solid #d0cef0;">
    <div style="font-size:20px;">🏢</div>
    <div style="font-weight:bold; color:#3d3a8c; font-size:14px;">会社員型</div>
    <div style="font-size:12px; color:#555; margin-top:4px;">組織でデザインを担当。チームへの貢献が中心。</div>
  </div>
  <div style="background:#fff8f0; border-radius:12px; padding:14px; border:1px solid #e8d4b0;">
    <div style="font-size:20px;">🌙</div>
    <div style="font-weight:bold; color:#b07030; font-size:14px;">副業スタート型</div>
    <div style="font-size:12px; color:#555; margin-top:4px;">本業を続けながら小さく案件を受け始める。</div>
  </div>
  <div style="background:#f0fff4; border-radius:12px; padding:14px; border:1px solid #b0dfc0;">
    <div style="font-size:20px;">🤝</div>
    <div style="font-weight:bold; color:#1a7a40; font-size:14px;">業務委託・インハウス型</div>
    <div style="font-size:12px; color:#555; margin-top:4px;">企業に入り込み、継続的に任される。</div>
  </div>
  <div style="background:#fff0f5; border-radius:12px; padding:14px; border:1px solid #f0b0c8;">
    <div style="font-size:20px;">⭐</div>
    <div style="font-weight:bold; color:#a0206a; font-size:14px;">自営業・専門家型</div>
    <div style="font-size:12px; color:#555; margin-top:4px;">自分の名前・専門性で直接選ばれる。</div>
  </div>
  <div style="background:#f5f0ff; border-radius:12px; padding:14px; border:1px solid #c8b0f0; grid-column:1/-1;">
    <div style="font-size:20px;">👑</div>
    <div style="font-weight:bold; color:#5a20a0; font-size:14px;">経営者・チーム型</div>
    <div style="font-size:12px; color:#555; margin-top:4px;">チームや仕組みで価値を届ける。思想・メソッドの言語化が鍵。</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("1DAYあたりの目安：**約30分**　答えに正解も不正解もありません。")
    if st.button("DAY 1 をスタートする", type="primary", use_container_width=True):
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

    col_img, col_txt = st.columns([1, 3])
    with col_img:
        st.markdown(
            f'<img src="data:image/jpeg;base64,{AVATAR}" '
            f'style="width:80px;height:80px;border-radius:50%;object-fit:cover;'
            f'object-position:top;border:2px solid #c9a96e;display:block;margin:0 auto;">',
            unsafe_allow_html=True,
        )
    with col_txt:
        st.markdown("### マイページ")
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
                if st.button("やり直す", key=f"restart_{i}", use_container_width=True):
                    opening = mgr.restart_day(i)
                    st.session_state.messages = [{"role": "assistant", "content": opening}]
                    st.session_state.screen = "chat"
                    _persist()
                    st.rerun()
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
        if current_day == 1:
            st.markdown("---")
            st.markdown("**働き方タイプ（参考）**")
            st.markdown("""
<div style="font-size:12px;">
🏢 <b>会社員型</b><br>
🌙 <b>副業スタート型</b><br>
🤝 <b>業務委託・インハウス型</b><br>
⭐ <b>自営業・専門家型</b><br>
👑 <b>経営者・チーム型</b>
</div>""", unsafe_allow_html=True)

    st.markdown(f"##### DAY {current_day} / {TOTAL_PARTS}　{mgr.current_part['name']}")

    # DAY開始時にワークシートを表示（最初のメッセージが1件のみ＝開始直後）
    if len(st.session_state.messages) == 1:
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

    # ── ブランディングノート生成・表示 ──────────────────────────────────
    st.markdown("---")
    st.markdown("### DAY {} ブランディングノート".format(completed))
    with st.spinner("ブランディングノートを作成しています..."):
        summary_text = mgr.part_summaries[-1] if mgr.part_summaries else ""
        note_img = generate_note_image(completed, mgr.route, summary_text)
    st.image(note_img, use_container_width=True)
    st.download_button(
        label="ブランディングノートをダウンロード（PNG）",
        data=note_img,
        file_name=f"branding_note_day{completed}.png",
        mime="image/png",
        use_container_width=True,
    )

    # DAY3完了時はLINEボタンを表示
    if mgr.finished:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#3d3a8c,#5a56b0);border-radius:16px;'
            'padding:24px;text-align:center;margin:16px 0;">'
            '<p style="color:#fff;font-size:16px;margin-bottom:8px;">'
            'ここまでできた仮説を、もっと深く一緒に整理しませんか？</p>'
            '<p style="color:rgba(255,255,255,0.8);font-size:14px;margin-bottom:16px;">'
            '肩書き・商品設計・発信・価格設計など、個別相談でサポートします。</p>'
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
        "　3DAYSセルフブランディングセッションまとめ",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        *section("現在地と目指す方向", "position"),
        *section("あなたのルート", "route"),
        *section("選ばれたい相手", "target"),
        *section("提供できること", "value"),
        *section("自分だからこその理由", "reason"),
        *section("肩書き仮説", "title_hypothesis"),
        *section("30秒自己紹介", "intro_30sec"),
        *section("SNSプロフィール文", "sns_profile"),
        *section("残っている不安", "anxiety"),
        *section("個別相談で深めるテーマ", "consultation"),
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "この言葉は、あなたの人生から生まれた大切な仮説です。",
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

    sections = [
        ("POSITION", "現在地と目指す方向", sheet.get("position", "")),
        ("ROADMAP", "ロードマップ（現在→1年後→3年後）", sheet.get("roadmap", "")),
        ("TARGET", "選ばれたい相手", sheet.get("target", "")),
        ("VALUE", "提供できること", sheet.get("value", "")),
        ("REASON", "自分だからこその理由", sheet.get("reason", "")),
        ("TITLE HYPOTHESIS", "肩書き仮説", sheet.get("title_hypothesis", "")),
        ("30秒自己紹介", "交流会・SNSで使える自己紹介", sheet.get("intro_30sec", "")),
        ("SNS PROFILE", "SNSプロフィール文", sheet.get("sns_profile", "")),
        ("ANXIETY", "残っている不安", sheet.get("anxiety", "")),
        ("NEXT STEP", "個別相談で深めるテーマ", sheet.get("consultation", "")),
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

    # ── LINEコンバージョンボタン ─────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="background:linear-gradient(135deg,#3d3a8c,#5a56b0);border-radius:16px;'
        'padding:24px;text-align:center;margin:16px 0;">'
        '<p style="color:#fff;font-size:16px;margin-bottom:8px;">'
        'ここまでできた仮説を、もっと深く一緒に整理しませんか？</p>'
        '<p style="color:rgba(255,255,255,0.8);font-size:14px;margin-bottom:16px;">'
        '肩書き・商品設計・発信・価格設計など、個別相談でサポートします。</p>'
        '<a href="https://lin.ee/yZCe0OW" target="_blank" style="'
        'display:inline-block;background:#06C755;color:#fff;font-weight:bold;'
        'font-size:18px;padding:14px 40px;border-radius:50px;text-decoration:none;">'
        'LINEで個別相談に申し込む</a>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
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
