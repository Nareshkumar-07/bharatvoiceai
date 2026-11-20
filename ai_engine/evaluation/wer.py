"""Word error rate with the standard S/D/I breakdown."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "").lower()
    t = re.sub(r"[^\w\s\u0900-\u0DFF\u0600-\u06FF']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text: str) -> list[str]:
    return normalise(text).split()


@dataclass
class ErrorStats:
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int
    hypothesis_length: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float:
        return self.errors / self.reference_length if self.reference_length else float("nan")

    def to_dict(self) -> dict:
        return {
            "substitutions": self.substitutions,
            "deletions": self.deletions,
            "insertions": self.insertions,
            "errors": self.errors,
            "reference_length": self.reference_length,
            "hypothesis_length": self.hypothesis_length,
            "rate": None if self.reference_length == 0 else round(self.rate, 4),
        }


def align(reference: list[str], hypothesis: list[str]) -> ErrorStats:
    n, m = len(reference), len(hypothesis)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    ops = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0], ops[i][0] = i, "d"
    for j in range(1, m + 1):
        dp[0][j], ops[0][j] = j, "i"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if reference[i - 1] == hypothesis[j - 1]:
                dp[i][j], ops[i][j] = dp[i - 1][j - 1], "="
            else:
                options = [
                    (dp[i - 1][j - 1] + 1, "s"),
                    (dp[i - 1][j] + 1, "d"),
                    (dp[i][j - 1] + 1, "i"),
                ]
                dp[i][j], ops[i][j] = min(options, key=lambda x: x[0])
    s = d = ins = 0
    i, j = n, m
    while i > 0 or j > 0:
        op = ops[i][j]
        if op == "=":
            i, j = i - 1, j - 1
        elif op == "s":
            s += 1
            i, j = i - 1, j - 1
        elif op == "d":
            d += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return ErrorStats(s, d, ins, n, m)


def wer(reference: str, hypothesis: str) -> ErrorStats:
    return align(tokens(reference), tokens(hypothesis))


def corpus_wer(pairs: list[tuple[str, str]]) -> dict:
    total_ref = total_err = 0
    per_utt = []
    for ref, hyp in pairs:
        stats = wer(ref, hyp)
        total_ref += stats.reference_length
        total_err += stats.errors
        per_utt.append(stats.to_dict())
    return {
        "wer": round(total_err / total_ref, 4) if total_ref else None,
        "reference_words": total_ref,
        "errors": total_err,
        "utterances": len(pairs),
        "per_utterance": per_utt,
    }
