"""セッションの進行・会話履歴・DAY切り替えを管理する。"""
import os
import anthropic
from .persona import TAKAMI_SYSTEM_PROMPT, PARTS, TOTAL_PARTS

# DAY終了を検知するマーカー（誤検知を防ぐため具体的なフレーズに絞る）
_DAY_END_MARKERS = [
    "今日はここまでにしましょう",
    "次のDAYに進みますか",
    "今日はここで終わりにして、また",
    "全3DAYS",
    "3DAYSセルフブランディングセッションまとめ",
]


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
        # 各DAY開始時点のhistoryインデックスを記録（やり直し用）
        self.day_start_indices: list[int] = [0]

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

    def start(self) -> str:
        opening = get_opening_message(0)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def resume_day(self) -> str:
        """次のDAYを開始して冒頭メッセージを返す。"""
        self.day_just_completed = False
        # このDAYの開始インデックスを記録
        if len(self.day_start_indices) <= self.part_index:
            self.day_start_indices.append(len(self.history))
        opening = get_opening_message(self.part_index)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def restart_day(self, day_index: int) -> str:
        """指定したDAY（0-indexed）をやり直す。それ以降の履歴と要約をリセット。"""
        # historyをそのDAYの開始時点まで巻き戻す
        if day_index < len(self.day_start_indices):
            self.history = self.history[:self.day_start_indices[day_index]]
        elif day_index == 0:
            self.history = []

        self.part_index = day_index
        self.part_summaries = self.part_summaries[:day_index]
        self.day_start_indices = self.day_start_indices[:day_index + 1]
        self.finished = False
        self.day_just_completed = False

        opening = get_opening_message(day_index)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def send(self, user_message: str) -> tuple[str, bool]:
        self.day_just_completed = False
        self.history.append({"role": "user", "content": user_message})

        system = build_part_system(self.part_index)
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
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

        if self.part_index < TOTAL_PARTS - 1:
            self.part_index += 1
            # 次のDAY開始インデックスを記録
            if len(self.day_start_indices) <= self.part_index:
                self.day_start_indices.append(len(self.history))
        else:
            self.finished = True

    def to_dict(self) -> dict:
        return {
            "part_index": self.part_index,
            "history": self.history,
            "part_summaries": self.part_summaries,
            "finished": self.finished,
            "day_just_completed": self.day_just_completed,
            "day_start_indices": self.day_start_indices,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionManager":
        mgr = cls()
        mgr.part_index = data["part_index"]
        mgr.history = data["history"]
        mgr.part_summaries = data["part_summaries"]
        mgr.finished = data["finished"]
        mgr.day_just_completed = data.get("day_just_completed", False)
        mgr.day_start_indices = data.get("day_start_indices", [0])
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
