"""セッションの進行・会話履歴・DAY切り替えを管理する。"""
import os
import anthropic
from .persona import TAKAMI_SYSTEM_PROMPT, PARTS, TOTAL_PARTS

# DAY終了を検知するマーカー
# 誤検知を防ぐため「2つ以上マッチ」または「確定フレーズ1つ」で終了と判定する
_DAY_END_DEFINITE = [
    # これ1つで確定（非常に具体的なフレーズのみ）
    "3DAYSセルフブランディングセッションまとめ",
    "全3DAYS、本当にお疲れ様でした",
]
_DAY_END_SOFT = [
    # これが2つ以上揃ったら終了
    "今日はここまでにしましょう",
    "お疲れ様でした",
    "ブランディングノートにまとめます",
    "今日はここで終わりにして",
]


def build_part_system(part_index: int, user_name: str = "") -> str:
    part = PARTS[part_index]
    name_line = (
        f"\n\n【ユーザーのお名前】\n"
        f"必ず「{user_name}さん」と名前で呼んでください。絶対に省略しないこと。"
        if user_name else ""
    )
    return (
        TAKAMI_SYSTEM_PROMPT
        + name_line
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
        self.route: str = ""  # side_job / inhouse / specialist / business_owner
        # 各DAY開始時点のhistoryインデックスを記録（やり直し用）
        self.day_start_indices: list[int] = [0]
        self.restart_counts: dict[int, int] = {}  # {day_index: 使用済み回数}
        self.user_name: str = ""

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

    def start(self, user_name: str = "") -> str:
        self.user_name = user_name
        opening = get_opening_message(0)
        if user_name:
            opening = opening.replace("はじめまして！", f"はじめまして、{user_name}さん！", 1)
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

    MAX_RESTARTS = 1  # 各DAYのやり直し上限

    def can_restart(self, day_index: int) -> bool:
        return self.restart_counts.get(day_index, 0) < self.MAX_RESTARTS

    def remaining_restarts(self, day_index: int) -> int:
        return max(0, self.MAX_RESTARTS - self.restart_counts.get(day_index, 0))

    def restart_day(self, day_index: int) -> str:
        """指定したDAY（0-indexed）をやり直す。各DAYにつき1回まで。"""
        if not self.can_restart(day_index):
            raise ValueError(f"DAY{day_index + 1} のやり直しは上限に達しています")

        self.restart_counts[day_index] = self.restart_counts.get(day_index, 0) + 1

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

    def _api_messages(self) -> list[dict]:
        """APIに渡す履歴を返す。先頭はuserである必要があるため調整する。"""
        msgs = self.history[:]
        # Anthropic API: 最初のメッセージはuserでなければならない
        while msgs and msgs[0]["role"] != "user":
            msgs = msgs[1:]
        # 長すぎる場合は直近60件に絞る（先頭がuserになるよう再調整）
        if len(msgs) > 60:
            msgs = msgs[-60:]
            while msgs and msgs[0]["role"] != "user":
                msgs = msgs[1:]
        return msgs

    def send(self, user_message: str) -> tuple[str, bool]:
        self.day_just_completed = False
        self.history.append({"role": "user", "content": user_message})

        system = build_part_system(self.part_index, self.user_name)
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system,
                messages=self._api_messages(),
            )
            reply = response.content[0].text
        except anthropic.RateLimitError:
            self.history.pop()
            raise RuntimeError("rate_limit")
        except anthropic.AuthenticationError:
            self.history.pop()
            raise RuntimeError("auth_error")
        except anthropic.APIStatusError as e:
            self.history.pop()
            if e.status_code == 529:
                raise RuntimeError("overloaded")
            raise RuntimeError(f"api_error:{e.status_code}")
        except Exception as e:
            self.history.pop()
            raise RuntimeError(f"unknown:{e}")

        self.history.append({"role": "assistant", "content": reply})

        day_done = self._detect_day_end(reply)
        if day_done:
            self._advance_day()

        return reply, day_done

    def _detect_day_end(self, text: str) -> bool:
        # 確定フレーズが1つでもあれば終了
        if any(m in text for m in _DAY_END_DEFINITE):
            return True
        # ソフトマーカーが2つ以上揃ったら終了
        soft_matches = sum(1 for m in _DAY_END_SOFT if m in text)
        return soft_matches >= 2

    def _advance_day(self):
        summary = self._extract_part_summary()
        self.part_summaries.append(summary)
        self.day_just_completed = True

        # DAY1完了時にルートを検知
        if self.part_index == 0:
            self.route = self._detect_route()

        if self.part_index < TOTAL_PARTS - 1:
            self.part_index += 1
            if len(self.day_start_indices) <= self.part_index:
                self.day_start_indices.append(len(self.history))
        else:
            self.finished = True

    def _current_day_history(self) -> list[dict]:
        """現在のDAYの会話履歴だけを返す。"""
        start = self.day_start_indices[self.part_index] if self.part_index < len(self.day_start_indices) else 0
        return self.history[start:]

    def _detect_route(self) -> str:
        """DAY1の診断結果メッセージ内の【〇〇型】からルートを判定する。
        見つからない場合はAPIで判定する。"""
        # 診断結果メッセージ内の【〇〇型】を直接探す（最も確実）
        type_map = {
            "副業スタート型": "side_job",
            "業務委託型":     "inhouse",
            "起業家型":       "specialist",
            "ディレクター型": "business_owner",
        }
        for msg in reversed(self.history):
            if msg["role"] == "assistant":
                for label, route in type_map.items():
                    if f"【{label}】" in msg["content"]:
                        return route

        # フォールバック：APIで判定
        day1_history = self._current_day_history()
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'AI'}: {m['content']}"
            for m in day1_history
        )
        prompt = (
            "以下はDAY1の会話記録です。AIが診断した働き方タイプから、最も適切なルートを1つ選んでください。\n"
            "回答は以下のいずれか1語のみ：side_job / inhouse / specialist / business_owner\n\n"
            f"【会話記録】\n{history_text}"
        )
        try:
            res = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = res.content[0].text.strip().lower()
            for r in ("side_job", "inhouse", "specialist", "business_owner"):
                if r in raw:
                    return r
        except Exception:
            pass
        return "specialist"  # デフォルト

    def to_dict(self) -> dict:
        return {
            "part_index": self.part_index,
            "history": self.history,
            "part_summaries": self.part_summaries,
            "finished": self.finished,
            "day_just_completed": self.day_just_completed,
            "route": self.route,
            "day_start_indices": self.day_start_indices,
            "restart_counts": self.restart_counts,
            "user_name": self.user_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionManager":
        mgr = cls()
        mgr.part_index = data["part_index"]
        mgr.history = data["history"]
        mgr.part_summaries = data["part_summaries"]
        mgr.finished = data["finished"]
        mgr.day_just_completed = data.get("day_just_completed", False)
        mgr.route = data.get("route", "")
        mgr.day_start_indices = data.get("day_start_indices", [0])
        # JSONはdictキーを文字列に変換するためintに戻す
        raw = data.get("restart_counts", {})
        mgr.restart_counts = {int(k): v for k, v in raw.items()}
        mgr.user_name = data.get("user_name", "")
        return mgr

    def _extract_part_summary(self) -> str:
        part = self.current_part
        day_msgs = self._current_day_history()
        extract_prompt = (
            f"以下はDAY「{part['name']}」の会話記録です。\n"
            "ユーザーが話した内容から、ブランディングに役立つ重要なポイントを箇条書きで3〜5つにまとめてください。\n"
            "ユーザー自身の言葉を活かして、具体的に書いてください。\n\n"
            "【会話記録】\n"
            + "\n".join(
                f"{'User' if m['role'] == 'user' else 'たかみ'}: {m['content']}"
                for m in day_msgs
            )
        )
        try:
            res = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": extract_prompt}],
            )
            return res.content[0].text
        except Exception:
            return f"（DAY{part['id']}のまとめ生成中にエラーが発生しました。会話内容は保存されています。）"
