"""DAY終了後のブランディングノート画像を生成する。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io

# カラーパレット
NAVY   = (26, 45, 90)
GOLD   = (201, 169, 110)
CREAM  = (250, 248, 244)
WHITE  = (255, 255, 255)
GRAY   = (90, 90, 90)
LIGHT  = (240, 235, 225)

FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansJP.otf"

# ルート表示名マッピング
ROUTE_LABEL = {
    "side_job":       "副業スタート型",
    "inhouse":        "業務委託・インハウス型",
    "specialist":     "自営業・専門家型",
    "business_owner": "経営者・チーム型",
}

DAY_TITLE = {
    1: "今のステージと、目指したい働き方を知る",
    2: "ルート別に、選ばれる理由を掘る",
    3: "肩書き・役割名・自己紹介に整える",
}

# DAY2/3のセクション定義（ルート・DAYごと）
SECTIONS = {
    (1, ""):  [
        ("現在地", "position"),
        ("目指したい方向", "direction"),
        ("今必要な言語化", "language"),
        ("DAY2で深掘りするテーマ", "day2_theme"),
    ],
    (2, "side_job"): [
        ("受けやすい仕事", "easy_work"),
        ("相性が良さそうな相手", "target"),
        ("今は避けた方が良い仕事", "avoid"),
        ("仮の立ち位置", "position"),
        ("残っている不安", "anxiety"),
    ],
    (2, "inhouse"): [
        ("得意な役割", "role"),
        ("力を発揮しやすい現場", "place"),
        ("チームに入るうえでの強み", "strength"),
        ("仮の立ち位置", "position"),
        ("残っている不安", "anxiety"),
    ],
    (2, "specialist"): [
        ("肩書きの種 3案", "seeds"),
        ("一番捨てきれないテーマ", "theme"),
        ("誰のための何屋か（3案）", "position"),
        ("残っている不安", "anxiety"),
    ],
    (2, "business_owner"): [
        ("作りたい方向性", "direction"),
        ("届けたい相手", "target"),
        ("自分が担いたい役割", "role"),
        ("仮の立ち位置", "position"),
        ("残っている不安", "anxiety"),
    ],
    (3, "side_job"): [
        ("肩書き案 3つ", "titles"),
        ("30秒自己紹介", "intro"),
        ("SNSプロフィール文", "profile"),
        ("次に試してみる場所", "next"),
        ("残っている不安", "anxiety"),
    ],
    (3, "inhouse"): [
        ("役割名・肩書き案 3つ", "titles"),
        ("30秒自己紹介", "intro"),
        ("SNSプロフィール文", "profile"),
        ("次に試してみる場所", "next"),
        ("残っている不安", "anxiety"),
    ],
    (3, "specialist"): [
        ("肩書き案 3つ", "titles"),
        ("選んだ肩書き", "chosen"),
        ("30秒自己紹介", "intro"),
        ("SNSプロフィール文", "profile"),
        ("残っている不安", "anxiety"),
    ],
    (3, "business_owner"): [
        ("役割名・肩書き案 3つ", "titles"),
        ("30秒自己紹介", "intro"),
        ("SNSプロフィール文", "profile"),
        ("次に試してみる場所", "next"),
        ("残っている不安", "anxiety"),
    ],
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """テキストを最大幅で折り返す。"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        # 1文字ずつチェックして折り返す
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
    """テキストを折り返しながら描画し、終端Y座標を返す。"""
    lines = _wrap_text(text or "（未記入）", font, max_width)
    line_h = font.size + 6
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
    return y


def generate_note_image(day: int, route: str, summary: str) -> bytes:
    """ブランディングノート画像をPNG bytesで返す。"""
    W, H = 1200, 1697
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    # フォント
    f_tiny   = _font(20)
    f_small  = _font(24)
    f_body   = _font(28)
    f_label  = _font(30)
    f_sub    = _font(36)
    f_title  = _font(48)
    f_day    = _font(72)

    MARGIN = 60
    content_w = W - MARGIN * 2

    # ── ヘッダー（ネイビー背景） ──────────────────────────────────────────
    header_h = 220
    draw.rectangle([0, 0, W, header_h], fill=NAVY)

    # 左：BRANDING NOTE タグ
    draw.rectangle([MARGIN, 30, MARGIN + 200, 65], fill=GOLD)
    draw.text((MARGIN + 10, 32), "BRANDING NOTE", font=f_small, fill=WHITE)

    # DAY番号
    draw.text((MARGIN, 70), f"DAY {day}", font=f_day, fill=WHITE)

    # タイトル
    title = DAY_TITLE.get(day, "")
    draw.text((MARGIN, 155), title, font=f_sub, fill=GOLD)

    # ルート表示（DAY2以降）
    if route and day > 1:
        route_label = ROUTE_LABEL.get(route, route)
        draw.text((W - MARGIN - 350, 75), route_label, font=f_label, fill=GOLD)

    # ── ゴールドライン ────────────────────────────────────────────────────
    draw.rectangle([0, header_h, W, header_h + 4], fill=GOLD)

    y = header_h + 30

    # ── サマリーテキストをセクションに分けて描画 ─────────────────────────
    # summaryはAIが生成した箇条書きテキスト - そのまま表示
    draw.text((MARGIN, y), "TODAY'S SESSION SUMMARY", font=f_label, fill=GOLD)
    y += 45
    draw.rectangle([MARGIN, y, W - MARGIN, y + 2], fill=GOLD)
    y += 20

    # サマリーテキストを描画
    max_w = content_w - 30
    y = _draw_text_block(draw, summary, MARGIN + 10, y, f_body, GRAY, max_w)
    y += 30

    # ── DAY1まとめ欄（全ルート共通） ─────────────────────────────────────
    if day == 1:
        sections_info = [
            "現在地",
            "目指したい方向",
            "今必要な言語化",
            "DAY2で深掘りするテーマ",
        ]
    elif day == 2:
        sections_info = {
            "side_job":       ["受けやすい仕事", "相性が良い相手", "仮の立ち位置", "残っている不安"],
            "inhouse":        ["得意な役割", "力を発揮しやすい現場", "仮の立ち位置", "残っている不安"],
            "specialist":     ["肩書きの種 3案", "一番捨てきれないテーマ", "誰のための何屋か", "残っている不安"],
            "business_owner": ["作りたい方向性", "届けたい相手", "仮の立ち位置", "残っている不安"],
        }.get(route, ["選ばれたい相手", "提供できること", "仮の立ち位置", "残っている不安"])
    else:
        sections_info = {
            "side_job":       ["肩書き案", "30秒自己紹介", "SNSプロフィール文", "残っている不安"],
            "inhouse":        ["役割名・肩書き案", "30秒自己紹介", "SNSプロフィール文", "残っている不安"],
            "specialist":     ["肩書き案", "選んだ肩書き", "30秒自己紹介", "残っている不安"],
            "business_owner": ["役割名・肩書き案", "30秒自己紹介", "SNSプロフィール文", "残っている不安"],
        }.get(route, ["肩書き仮説", "30秒自己紹介", "SNSプロフィール文", "残っている不安"])

    # セクション見出しのみ表示（内容はサマリーに含まれる）
    if y < H - 300:
        draw.text((MARGIN, y), "TODAY'S TAKEAWAYS", font=f_label, fill=GOLD)
        y += 45
        draw.rectangle([MARGIN, y, W - MARGIN, y + 2], fill=GOLD)
        y += 20

        for sec in sections_info:
            if y > H - 120:
                break
            # セクション背景
            box_h = 80
            draw.rectangle([MARGIN, y, W - MARGIN, y + box_h], fill=LIGHT, outline=GOLD, width=1)
            draw.rectangle([MARGIN, y, MARGIN + 6, y + box_h], fill=GOLD)
            draw.text((MARGIN + 20, y + 25), sec, font=f_label, fill=NAVY)
            y += box_h + 10

    # ── ロードマップセクション ─────────────────────────────────────────────
    if y < H - 250:
        y += 10
        draw.text((MARGIN, y), "ROADMAP", font=f_label, fill=GOLD)
        y += 45
        draw.rectangle([MARGIN, y, W - MARGIN, y + 2], fill=GOLD)
        y += 16

        steps = [
            ("現在", NAVY),
            ("1年後", (80, 120, 180)),
            ("3年後", GOLD),
        ]
        step_w = (content_w - 20) // 3
        for idx, (label, color) in enumerate(steps):
            sx = MARGIN + idx * (step_w + 10)
            draw.rectangle([sx, y, sx + step_w, y + 90], fill=LIGHT, outline=color, width=2)
            draw.rectangle([sx, y, sx + step_w, y + 34], fill=color)
            # ラベルを中央揃え
            bbox = f_label.getbbox(label)
            lw = bbox[2] - bbox[0]
            draw.text((sx + (step_w - lw) // 2, y + 6), label, font=f_label, fill=WHITE)
            # 矢印
            if idx < 2:
                draw.text((sx + step_w + 2, y + 35), "->", font=f_body, fill=GRAY)
        y += 110

    # ── フッター ─────────────────────────────────────────────────────────
    draw.rectangle([0, H - 60, W, H], fill=NAVY)
    draw.text((MARGIN, H - 42), "BRANDING NOTE", font=f_small, fill=GOLD)
    day_str = f"DAY {day}"
    if route and day > 1:
        day_str += f"  |  {ROUTE_LABEL.get(route, '')}"
    bbox = f_small.getbbox(day_str)
    tw = bbox[2] - bbox[0]
    draw.text((W - MARGIN - tw, H - 42), day_str, font=f_small, fill=GOLD)

    # bytesに変換
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
