"""DAY終了後のブランディングノート画像を生成する。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansJP.otf"
WORKSHEET_DIR = Path(__file__).parent.parent / "assets" / "worksheets"

# ワークシートごとの穴埋めエリア座標 (y_start, y_end)
# PIL スキャンで検出した空白エリア（1055x1491 画像）
FILL_COORDS: dict[str, list[tuple[int, int]]] = {
    "day1": [
        (643, 691),   # 現在地
        (731, 779),   # 目指したい方向
        (819, 867),   # 今必要な言語化
        (952, 1000),  # DAY2で深掘りするテーマ
    ],
    "day2_side_job": [
        (808, 932),   # 受けやすい仕事 / 相性の良い相手
        (1225, 1272), # 仮の立ち位置
        (1321, 1409), # 残っている不安
    ],
    "day2_inhouse": [
        (808, 922),   # 得意な役割 / 力を発揮しやすい現場
        (1234, 1275), # 仮の立ち位置
        (1325, 1407), # 残っている不安
    ],
    "day2_specialist": [
        (794, 865),   # 肩書きの種 3案
        (1252, 1295), # 一番捨てきれないテーマ
        (1343, 1417), # 誰のための何屋か（仮の立ち位置）
    ],
    "day3_side_job": [
        (1266, 1309), # 肩書き案
        (1356, 1414), # SNSプロフィール文
    ],
    "day3_inhouse": [
        (708, 749),   # 役割名・肩書き案
        (1378, 1426), # SNSプロフィール文
    ],
    "day3_specialist": [
        (699, 755),   # 肩書き案
        (1377, 1429), # SNSプロフィール文
    ],
}

# DAYごと・フィルエリアインデックスに対応する検索キー
SECTION_KEYS: dict[str, list[list[str]]] = {
    "day1": [
        ["現在地"],
        ["目指したい方向"],
        ["今必要な言語化"],
        ["DAY2で深掘り"],
    ],
    "day2_side_job": [
        ["選ばれたい相手", "受けやすい仕事", "提供できること"],
        ["仮の立ち位置"],
        ["残っている不安"],
    ],
    "day2_inhouse": [
        ["得意な役割", "力を発揮", "提供できること"],
        ["仮の立ち位置"],
        ["残っている不安"],
    ],
    "day2_specialist": [
        ["肩書きの種"],
        ["一番捨てきれない"],
        ["誰のための", "仮の立ち位置"],
    ],
    "day3_side_job": [
        ["肩書き", "役割名"],
        ["SNSプロフィール", "30秒自己紹介"],
    ],
    "day3_inhouse": [
        ["役割名", "肩書き"],
        ["SNSプロフィール", "30秒自己紹介"],
    ],
    "day3_specialist": [
        ["肩書き"],
        ["SNSプロフィール", "30秒自己紹介"],
    ],
}

# DAYごとのまとめマーカー
SUMMARY_MARKER = {
    1: "【DAY1まとめ】",
    2: "【DAY2まとめ】",
    3: "【3DAYS",
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            test = current + char
            bbox = font.getbbox(test)
            w = bbox[2] - bbox[0]
            if w > max_width:
                if current:
                    lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def _draw_text_block(draw: ImageDraw.Draw, text: str, x: int, y: int,
                     font: ImageFont.FreeTypeFont, color: tuple,
                     max_width: int) -> int:
    lines = _wrap_text(text or "（未記入）", font, max_width)
    line_h = font.size + 6
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
    return y


def _extract_section(history: list, day: int, ws_key: str, idx: int) -> str:
    """会話履歴からDAYまとめメッセージを探し、指定インデックスのセクションを抽出する。"""
    marker = SUMMARY_MARKER.get(day, "")
    keys = SECTION_KEYS.get(ws_key, [])
    if idx >= len(keys):
        return ""

    # まとめメッセージを探す（最後のassistantメッセージから逆順）
    summary_text = ""
    for msg in reversed(history):
        if msg["role"] == "assistant" and marker in msg["content"]:
            summary_text = msg["content"]
            break

    if not summary_text:
        return ""

    # まとめ以降のテキストだけに絞る
    if marker in summary_text:
        summary_text = summary_text[summary_text.index(marker):]

    # 指定のキーに対応する行を探して値を返す
    search_keys = keys[idx]
    for line in summary_text.split("\n"):
        for key in search_keys:
            if key in line and "：" in line:
                return line.split("：", 1)[1].strip()
    return ""


def generate_note_image(day: int, route: str, summary: str, history: list = None) -> bytes:
    """ブランディングノート画像をPNG bytesで返す。

    ワークシート画像が存在する場合はそれを背景として穴埋め表示する。
    存在しない場合は従来の PIL 生成にフォールバック。
    """
    ws_key = "day1" if day == 1 else f"day{day}_{route}"
    ws_path = WORKSHEET_DIR / f"{ws_key}.png"
    coords = FILL_COORDS.get(ws_key, [])

    if ws_path.exists() and coords:
        img = Image.open(ws_path).convert("RGB")
        W, H = img.size
        draw = ImageDraw.Draw(img)

        f_fill = _font(20)
        TEXT_X = 40
        MAX_W = W - TEXT_X * 2

        for i, (y_start, y_end) in enumerate(coords):
            text = _extract_section(history or [], day, ws_key, i) if history else ""
            if not text:
                continue
            # 白背景で既存の空白を確保したうえにテキスト描画
            draw.rectangle([TEXT_X - 4, y_start + 2, W - TEXT_X + 4, y_end - 2],
                           fill=(255, 255, 255))
            _draw_text_block(draw, text, TEXT_X, y_start + 6, f_fill, (40, 40, 40), MAX_W)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()

    # ── フォールバック：PIL で新規生成 ─────────────────────────────────────
    NAVY  = (26, 45, 90)
    GOLD  = (201, 169, 110)
    CREAM = (250, 248, 244)
    WHITE = (255, 255, 255)
    GRAY  = (90, 90, 90)
    LIGHT = (240, 235, 225)

    ROUTE_LABEL = {
        "side_job":       "副業スタート型",
        "inhouse":        "業務委託型",
        "specialist":     "起業家型",
        "business_owner": "ディレクター型",
    }
    DAY_TITLE = {
        1: "今のステージと、目指したい働き方を知る",
        2: "ルート別に、選ばれる理由を掘る",
        3: "肩書き・役割名・自己紹介に整える",
    }

    W, H = 1200, 1697
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    f_small = _font(24)
    f_body  = _font(28)
    f_label = _font(30)
    f_sub   = _font(36)
    f_day   = _font(72)

    MARGIN = 60
    content_w = W - MARGIN * 2

    # ヘッダー
    header_h = 220
    draw.rectangle([0, 0, W, header_h], fill=NAVY)
    draw.rectangle([MARGIN, 30, MARGIN + 200, 65], fill=GOLD)
    draw.text((MARGIN + 10, 32), "BRANDING NOTE", font=f_small, fill=WHITE)
    draw.text((MARGIN, 70), f"DAY {day}", font=f_day, fill=WHITE)
    title = DAY_TITLE.get(day, "")
    draw.text((MARGIN, 155), title, font=f_sub, fill=GOLD)
    if route and day > 1:
        route_label = ROUTE_LABEL.get(route, route)
        draw.text((W - MARGIN - 350, 75), route_label, font=f_label, fill=GOLD)
    draw.rectangle([0, header_h, W, header_h + 4], fill=GOLD)

    y = header_h + 30

    # サマリー
    draw.text((MARGIN, y), "TODAY'S SESSION SUMMARY", font=f_label, fill=GOLD)
    y += 45
    draw.rectangle([MARGIN, y, W - MARGIN, y + 2], fill=GOLD)
    y += 20
    y = _draw_text_block(draw, summary, MARGIN + 10, y, f_body, GRAY, content_w - 30)
    y += 20

    # フッター
    draw.rectangle([0, H - 60, W, H], fill=NAVY)
    draw.text((MARGIN, H - 42), "BRANDING NOTE", font=f_small, fill=GOLD)
    day_str = f"DAY {day}"
    if route and day > 1:
        day_str += f"  |  {ROUTE_LABEL.get(route, '')}"
    bbox = f_small.getbbox(day_str)
    tw = bbox[2] - bbox[0]
    draw.text((W - MARGIN - tw, H - 42), day_str, font=f_small, fill=GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
