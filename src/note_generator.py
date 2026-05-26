"""DAY終了後のブランディングノート画像を生成する。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansJP.otf"
WORKSHEET_DIR = Path(__file__).parent.parent / "assets" / "worksheets"

# ワークシートごとの穴埋めエリア座標 (y_start, y_end)
# day1.png のみ対応（1055x1491 画像）
FILL_COORDS: dict[str, list[tuple[int, int]]] = {
    "day1": [
        (643, 691),   # 現状のタイプ
        (731, 779),   # 今の働き方
        (819, 1000),  # 課題・モヤモヤ
    ],
}

# DAYごと・フィルエリアインデックスに対応する検索キー
SECTION_KEYS: dict[str, list[list[str]]] = {
    "day1": [
        ["現状のタイプ"],
        ["今の働き方"],
        ["課題・モヤモヤ"],
    ],
}

# DAYごとのまとめマーカー
SUMMARY_MARKER = {
    1: "【DAY1まとめ】",
    2: "【DAY2まとめ】",
    3: "【DAY3まとめ】",
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
        1: "今の働き方を整理する",
        2: "理想の状態を言語化する",
        3: "現実と理想のギャップを整理する",
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
    bbox = f_small.getbbox(day_str)
    tw = bbox[2] - bbox[0]
    draw.text((W - MARGIN - tw, H - 42), day_str, font=f_small, fill=GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
