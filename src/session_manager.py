"""セッションの進行・会話履歴・パート切り替えを管理する。"""
import os
import anthropic
from .persona import TAKAMI_SYSTEM_PROMPT, PARTS, TOTAL_PARTS

# たかみが次のパートへ移行するときに使うマーカーフレーズ
_TRANSITION_MARKERS = [
    "次のパートに進みましょう",
    "では次は",
    "次は、",
    "次のテーマに移りましょう",
    "最後のパート",
    "いよいよ最後",
]


def build_part_system(part_index: int) -> str:
    """現在のパート情報をシステムプロンプトに追記して返す。"""
    part = PARTS[part_index]
    return (
        TAKAMI_SYSTEM_PROMPT
        + f"\n\n【現在のパート】\n"
        + f"パート {part['id']} / {TOTAL_PARTS}：{part['name']}\n"
        + f"テーマ：{part['theme']}\n"
        + f"進め方のヒント：{part['guide']}"
    )


def get_opening_message(part_index: int) -> str:
    return PARTS[part_index]["opening"]


class SessionManager:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.part_index: int = 0
        self.history: list[dict] = []
        self.part_summaries: list[str] = []
        self.finished: bool = False

    @property
    def current_part(self) -> dict:
        return PARTS[self.part_index]

    @property
    def part_number(self) -> int:
        return self.part_index + 1

    def start(self) -> str:
        """セッション開始。最初のたかみのメッセージを返す。"""
        opening = get_opening_message(0)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def send(self, user_message: str) -> tuple[str, bool]:
        """ユーザーメッセージを送り、たかみの返答と「パート完了したか」を返す。"""
        self.history.append({"role": "user", "content": user_message})

        system = build_part_system(self.part_index)
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=self.history,
        )
        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})

        part_done = self._detect_transition(reply)
        if part_done:
            self._advance_part()

        return reply, part_done

    def _detect_transition(self, text: str) -> bool:
        return any(marker in text for marker in _TRANSITION_MARKERS)

    def _advance_part(self):
        """パートの要点を抽出して保存し、次のパートへ進む。"""
        summary = self._extract_part_summary()
        self.part_summaries.append(summary)

        if self.part_index < TOTAL_PARTS - 1:
            self.part_index += 1
        else:
            self.finished = True

    def _extract_part_summary(self) -> str:
        """現在のパートの会話から要点テキストを抽出する。"""
        part = self.current_part
        extract_prompt = (
            f"以下はパート「{part['name']}」の会話記録です。\n"
            "ユーザーが話した内容から、ブランディングに役立つ重要なポイントを箇条書きで3〜5つにまとめてください。\n"
            "ユーザー自身の言葉を活かして、具体的に書いてください。\n\n"
            "【会話記録】\n"
            + "\n".join(
                f"{'User' if m['role'] == 'user' else 'たかみ'}: {m['content']}"
                for m in self.history
            )
        )
        res = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        return res.content[0].text
