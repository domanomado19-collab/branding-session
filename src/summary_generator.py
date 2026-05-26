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

    prompt = f"""以下は「3days MINE BRANDING」の3DAYSセッション記録です。
この内容をもとに、以下の項目を生成してください。日本語で記述し、ユーザー自身の言葉を活かしてください。

【セッション記録】
{parts_text}

---

## 現状のタイプ
side_job / inhouse / specialist / business_owner のどれかを記載（例：side_job）。

## 今の働き方
現在の働き方・状況を1〜2文で具体的に書く。

## 課題・モヤモヤ
DAY1で話してくれた課題やモヤモヤを箇条書きで3〜5つ。ユーザーの言葉を活かす。

## 理想のタイプ
side_job / inhouse / specialist / business_owner のどれかを記載。

## 実現したい時期
何年後に実現したいかを記載（例：2年後）。

## なぜなりたいか
そのタイプを目指す理由・動機を2〜3文で。ユーザーの言葉を活かす。

## そうなれたら嬉しいこと
理想を実現したときに何が変わって嬉しいか・どう変わるかを2〜3文で具体的に。

## デザインスキルのギャップ
現状のスキルレベルと足りている部分・課題を整理し、優先度（高/中/低）と理由を記載。

## ブランディングのギャップ
現状の見せ方・発信の状況と課題を整理し、優先度（高/中/低）と理由を記載。

## 営業・集客・ビジネス視点のギャップ
現状の仕事の取り方・単価・集客の課題を整理し、優先度（高/中/低）と理由を記載。

## まず取り組むべきこと
3つのギャップを踏まえて、最初に取り組むべきことを1〜2項目、具体的にレコメンドする。なぜそれを最初に勧めるかの理由も一言添える。
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
    except Exception as e:
        raw = f"（ブランディングシートの生成中にエラーが発生しました: {e}）"
    return _parse_sheet(raw)


def _parse_sheet(text: str) -> dict:
    sections = {
        "current_type": "",
        "current_situation": "",
        "current_struggles": "",
        "ideal_type": "",
        "ideal_timeline": "",
        "ideal_reason": "",
        "ideal_benefits": "",
        "design_skill_gaps": "",
        "branding_gaps": "",
        "business_gaps": "",
        "priority_actions": "",
        "raw": text,
    }

    mappings = {
        "現状のタイプ": "current_type",
        "今の働き方": "current_situation",
        "課題・モヤモヤ": "current_struggles",
        "理想のタイプ": "ideal_type",
        "実現したい時期": "ideal_timeline",
        "なぜなりたいか": "ideal_reason",
        "そうなれたら嬉しいこと": "ideal_benefits",
        "デザインスキルのギャップ": "design_skill_gaps",
        "ブランディングのギャップ": "branding_gaps",
        "営業・集客・ビジネス視点のギャップ": "business_gaps",
        "まず取り組むべきこと": "priority_actions",
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
