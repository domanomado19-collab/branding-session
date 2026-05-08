"""6パート分の要点からブランディングシートを生成する。"""
import os
import anthropic
from .persona import PARTS


def generate_branding_sheet(part_summaries: list[str]) -> dict:
    """パートごとの要約を受け取り、ブランディングシートを辞書で返す。"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    parts_text = "\n\n".join(
        f"【パート{i+1}：{PARTS[i]['name']}】\n{summary}"
        for i, summary in enumerate(part_summaries)
    )

    prompt = f"""以下はフリーランスデザイナーのブランディングセッションから抽出した情報です。
この情報をもとに、以下の項目を生成してください。
出力は各項目を明確に分けて、日本語で記述してください。
ユーザー自身の言葉やエピソードを活かして、具体的で温かみのある文章にしてください。

【セッション情報】
{parts_text}

---

【出力してほしい項目】

## ブランドコンセプト
「私は〇〇のための△△デザイナー」の形で、ターゲットと提供価値を一文で表現する。
ユーザーの人生ストーリーと価値が繋がっていることが伝わる言葉にする。

## 肩書き
シンプルで覚えやすい肩書きを1〜2案提示する。（例：「美容サロン専門の集客デザイナー」）

## テクニカルスキル
デザイン面での得意なこと・ツール・制作ジャンルを箇条書きで列挙する。

## パーソナルスキル
コミュニケーション・提案力・共感力など、人として・仕事スタイルとしての強みを箇条書きで列挙する。

## ストーリー（なぜあなたが選ばれるか）
人生の経験とデザイナーとしての価値が繋がる理由を2〜3文で表現する。
「だからこそ、この人たちの気持ちがわかる」という必然性が伝わるように書く。

## ターゲット顧客像
一番相性のいいクライアントを2〜3文で具体的に描写する。

## 目標設定
理想の働き方（稼働スタイル）と月商・年商のイメージを2〜3文でまとめる。

## 30秒自己紹介フレーズ
交流会やSNSで使える自己紹介を150字以内で作成する。
「誰のためのデザイナーか」「何が違うか」「何を提供できるか」が伝わる自然な文体にする。

## 次のアクション
このブランディングシートをもとに、今すぐ取り組める具体的なアクションを3〜5つ、優先度順に提案する。
「〜を作る」「〜を変更する」「〜を発信する」など動詞で始まる具体的な行動で書く。
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    return _parse_sheet(raw)


def _parse_sheet(text: str) -> dict:
    """マークダウン形式のテキストをセクションごとに辞書に変換する。"""
    sections = {
        "brand_concept": "",
        "title": "",
        "technical_skills": "",
        "personal_skills": "",
        "story": "",
        "target_client": "",
        "goals": "",
        "intro_phrase": "",
        "roadmap": "",
        "raw": text,
    }

    mappings = {
        "ブランドコンセプト": "brand_concept",
        "肩書き": "title",
        "テクニカルスキル": "technical_skills",
        "パーソナルスキル": "personal_skills",
        "ストーリー": "story",
        "ターゲット顧客像": "target_client",
        "目標設定": "goals",
        "30秒自己紹介フレーズ": "intro_phrase",
        "次のアクション": "roadmap",
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
