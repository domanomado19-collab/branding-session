"""セッションの進行・会話履歴・DAY切り替えを管理する。"""
import os
import anthropic
from .persona import TAKAMI_SYSTEM_PROMPT, PARTS, TOTAL_PARTS

_DAY_END_MARKERS = [
    "今日はここまで",
    "お疲れ様でした",
    "次のDAYでは",
    "次回は",
    "また次回",
    "全6DAY",
    "いよいよ最終DAY",
]

# 1DAYあたりの想定交流回数（これを100%とする）
_TARGET_EXCHANGES = 5


def build_part_system(part_index: int) -> str:
    part = PARTS[part_index]
    return (
        TAKAMI_SYSTEM_PROMPT
        + f"\n\n【現在のDAY】\n"
        + f"DAY {part['id']} / {TOTAL_PARTS}：{part['name']}\n"
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
        self.day_just_completed: bool = False
        self.day_exchange_count: int = 0  # 現在のDAY内での交流回数

    @property
    def current_part(self) -> dict:
        return PARTS[self.part_index]

    @property
    def part_number(self) -> int:
        return self.part_index + 1

    @property
    def completed_days(self) -> int:
        return len(self.part_summaries)

    @property
    def overall_progress_pct(self) -> int:
        return int(self.completed_days / TOTAL_PARTS * 100)

    @property
    def day_progress_pct(self) -> int:
        """現在のDAY内の進捗（0〜99%。完了時は呼ばれない）。"""
        pct = int(self.day_exchange_count / _TARGET_EXCHANGES * 100)
        return min(pct, 99)

    def start(self) -> str:
        opening = get_opening_message(0)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def resume_day(self) -> str:
        """次のDAYを開始して冒頭メッセージを返す。"""
        self.day_just_completed = False
        self.day_exchange_count = 0
        opening = get_opening_message(self.part_index)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def send(self, user_message: str) -> tuple[str, bool]:
        self.day_just_completed = False
        self.history.append({"role": "user", "content": user_message})
        self.day_exchange_count += 1

        system = build_part_system(self.part_index)
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=self.history,
        )
        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})

        day_done = self._detect_day_end(reply)
        if day_done:
            self._advance_day()

        return reply, day_done

    def _detect_day_end(self, text: str) -> bool:
        return any(marker in text for marker in _DAY_END_MARKERS)

    def _advance_day(self):
        summary = self._extract_part_summary()
        self.part_summaries.append(summary)
        self.day_just_completed = True
        self.day_exchange_count = 0

        if self.part_index < TOTAL_PARTS - 1:
            self.part_index += 1
        else:
            self.finished = True

    def to_dict(self) -> dict:
        return {
            "part_index": self.part_index,
            "history": self.history,
            "part_summaries": self.part_summaries,
            "finished": self.finished,
            "day_just_completed": self.day_just_completed,
            "day_exchange_count": self.day_exchange_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionManager":
        mgr = cls()
        mgr.part_index = data["part_index"]
        mgr.history = data["history"]
        mgr.part_summaries = data["part_summaries"]
        mgr.finished = data["finished"]
        mgr.day_just_completed = data.get("day_just_completed", False)
        mgr.day_exchange_count = data.get("day_exchange_count", 0)
        return mgr

    def _extract_part_summary(self) -> str:
        part = self.current_part
        extract_prompt = (
            f"以下はDAY「{part['name']}」の会話記録です。\n"
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
