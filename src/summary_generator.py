"""3DAYSセッションのまとめからブランディングシートを生成する。"""
import os
import anthropic
from .persona import PARTS


def generate_branding_sheet(part_summaries: list[str]) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    parts_text = "\n\n".join(
        f"【DAY{i+1}：{PARTS[i]['name']}】\n{summary}"
        for i, summary in enumerate(part_summaries)
    )

    prompt = f"""以下は「選ばれる肩書きをつくる 3DAYSセルフブランディングセッション」の記録です。
この内容をもとに、以下の項目を生成してください。日本語で記述し、ユーザー自身の言葉を活かしてください。

【セッション記録】
{parts_text}

---

## 現在地と目指す方向
現在地（〇〇型）と目指したい方向（〇〇型）を1〜2文でまとめる。

## ロードマップ
セッションの内容をもとに、以下の時系列で整理する（各1〜2文）：
・現在：今の働き方・ステージ
・1年後：目指したい姿（具体的なアクションや変化）
・3年後：理想の姿（どのタイプの働き方になっていたいか）
ユーザーの言葉を活かして、前向きで具体的に書く。

## ルート
side_job / inhouse / specialist / business_owner のどれかを記載。

## 選ばれたい相手
一番相性のいいクライアント・現場を2〜3文で描写する。

## 提供できること
自分が役に立てること・提供できる価値を箇条書きで3〜5つ。

## 自分だからこその理由
なぜこの人が選ばれるのか、人生・経験・偏愛との接続を2〜3文で書く。

## 肩書き仮説
試しに名乗れる肩書き・役割名を1〜3案、箇条書きで。

## 30秒自己紹介
実際に使える自己紹介文を150字程度で。自然な文体で。

## SNSプロフィール文
プロフィール欄に使える短い文章を80字程度で。

## 残っている不安
まだ解決されていない不安・疑問を箇条書きで3〜5つ。

## 個別相談テーマ
次に個別相談で深めるべきテーマを1〜2文で。
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    return _parse_sheet(raw)


def _parse_sheet(text: str) -> dict:
    sections = {
        "position": "",
        "roadmap": "",
        "route": "",
        "target": "",
        "value": "",
        "reason": "",
        "title_hypothesis": "",
        "intro_30sec": "",
        "sns_profile": "",
        "anxiety": "",
        "consultation": "",
        "raw": text,
    }

    mappings = {
        "現在地と目指す方向": "position",
        "ロードマップ": "roadmap",
        "ルート": "route",
        "選ばれたい相手": "target",
        "提供できること": "value",
        "自分だからこその理由": "reason",
        "肩書き仮説": "title_hypothesis",
        "30秒自己紹介": "intro_30sec",
        "SNSプロフィール文": "sns_profile",
        "残っている不安": "anxiety",
        "個別相談テーマ": "consultation",
    }

    current_key = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        matched = False
        for heading, key in mappings.items():
            if stripped.startswith("##") and heading in stripped:
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched and current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
