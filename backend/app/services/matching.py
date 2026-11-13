"""Deterministic port of frontend/src/utils/matching.ts; no private learning records."""

from dataclasses import dataclass, field
from math import floor


CATEGORIES = ("考研", "考公", "四六级", "编程开发", "算法竞赛", "专业课程", "职业技能", "阅读写作")
STYLES = ("安静自习", "番茄钟", "语音陪伴", "定期复盘", "任务互督", "独立学习", "相互监督", "共同讨论")
STAGES = ("入门", "基础", "强化", "冲刺")
MATCHING_TIMEZONES = ("Asia/Shanghai", "Asia/Hong_Kong")


@dataclass(frozen=True)
class TimeSlot:
    day: int
    start: int
    end: int


@dataclass
class MatchingProfile:
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    time_slots: list[TimeSlot] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    stage: str | None = None


def round_score(value: float) -> int:
    # Python round uses bankers' rounding; match JavaScript Math.round instead.
    return floor(max(0, min(100, value)) + 0.5)


def normalize(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def jaccard(left: list[str], right: list[str]) -> float | None:
    a, b = normalize(left), normalize(right)
    return len(a & b) / len(a | b) if a and b else None


def goal_similarity(a: MatchingProfile, b: MatchingProfile) -> int:
    parts = [(jaccard(a.categories, b.categories), 0.65), (jaccard(a.tags, b.tags), 0.35)]
    known = [(value, weight) for value, weight in parts if value is not None]
    if not known:
        return 50
    return round_score(100 * sum(value * weight for value, weight in known) / sum(weight for _, weight in known))


def merge_intervals(slots: list[TimeSlot], day: int) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for slot in sorted((s for s in slots if s.day == day and s.end > s.start), key=lambda s: s.start):
        if not merged or slot.start > merged[-1][1]:
            merged.append((slot.start, slot.end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], slot.end))
    return merged


def time_similarity(left: list[TimeSlot], right: list[TimeSlot]) -> tuple[int, int]:
    if not left or not right:
        return 50, 0
    left_total = right_total = overlap = 0
    for day in range(1, 8):
        a, b = merge_intervals(left, day), merge_intervals(right, day)
        left_total += sum(end - start for start, end in a)
        right_total += sum(end - start for start, end in b)
        overlap += sum(max(0, min(y, v) - max(x, u)) for x, y in a for u, v in b)
    total = min(left_total, right_total)
    return (round_score(overlap / total * 100) if total else 0), overlap


def calculate_match(a: MatchingProfile, b: MatchingProfile) -> dict:
    goal = goal_similarity(a, b)
    time, overlap = time_similarity(a.time_slots, b.time_slots)
    method_j = jaccard(a.styles, b.styles)
    method = round_score(method_j * 100) if method_j is not None else 50
    level = 50
    if a.stage in STAGES and b.stage in STAGES:
        level = (100, 70, 40, 10)[abs(STAGES.index(a.stage) - STAGES.index(b.stage))]

    reasons, caveats = [], []
    for label, left, right in (
        ("共同方向：", a.categories, b.categories),
        ("目标标签契合：", a.tags, b.tags),
    ):
        shared = sorted(normalize(left) & normalize(right))
        if shared:
            reasons.append(label + "、".join(shared[:2]))
    if overlap:
        reasons.append(f"每周可共同学习 {overlap} 分钟")
    shared_styles = sorted(set(a.styles) & set(b.styles))
    if shared_styles:
        reasons.append("都偏好" + "、".join(shared_styles[:2]))
    if a.stage and a.stage == b.stage:
        reasons.append(f"同处{a.stage}阶段")
    if not a.categories or not b.categories or not a.tags or not b.tags:
        caveats.append("部分方向或目标标签未填写，目标分仅使用可比较的资料；均缺失时为 50 分")
    if not a.time_slots or not b.time_slots:
        caveats.append("一方尚未完善学习时段，时间分按 50 分中性值计算")
    elif not overlap:
        caveats.append("当前可用时段没有重合")
    if not a.styles or not b.styles:
        caveats.append("一方尚未设置学习方式，方式分按 50 分中性值计算")
    if not a.stage or not b.stage:
        caveats.append("一方尚未设置学习阶段，阶段分按 50 分中性值计算")
    return {
        "score": round_score(0.4 * goal + 0.35 * time + 0.15 * method + 0.1 * level),
        "dimensions": {"goal": goal, "time": time, "method": method, "level": level},
        "overlapMinutes": overlap,
        "reasons": reasons or ["暂无已知共同偏好，可先完善学习资料"],
        "caveats": caveats,
    }
