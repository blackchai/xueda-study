import pytest

from app.services.matching import MatchingProfile, TimeSlot, calculate_match, goal_similarity, round_score, time_similarity


def cpp(start=19 * 60, end=22 * 60):
    return MatchingProfile(["编程开发"], ["C++"], [TimeSlot(1, start, end)], ["共同讨论"], "强化")


def test_identical_and_realistic_weekly_overlap():
    assert calculate_match(cpp(), cpp())["score"] == 100
    result = calculate_match(cpp(), cpp(19 * 60 + 30, 22 * 60 + 30))
    assert result["dimensions"] == {"goal": 100, "time": 83, "method": 100, "level": 100}
    assert result["score"] == 94
    assert result["overlapMinutes"] == 150
    assert "每周可共同学习 150 分钟" in result["reasons"]


def test_missing_preferences_are_neutral_and_explained():
    result = calculate_match(MatchingProfile(), MatchingProfile())
    assert result["score"] == 50
    assert list(result["dimensions"].values()) == [50] * 4
    assert len(result["caveats"]) == 4


def test_goals_normalize_case_spaces_and_duplicates_without_changing_cpp():
    a = MatchingProfile(["编程开发", "编程开发"], [" C++ ", "PYTHON", "python"])
    b = MatchingProfile(["编程开发"], ["c++", "python"])
    assert goal_similarity(a, b) == 100
    b.tags = ["C#"]
    assert goal_similarity(a, b) == 65
    b.tags = []
    assert goal_similarity(a, b) == 100


def test_overlap_is_merged_and_never_double_counted():
    left = [TimeSlot(1, 1140, 1260), TimeSlot(1, 1200, 1320), TimeSlot(1, 1140, 1260)]
    right = [TimeSlot(1, 1170, 1350)]
    assert time_similarity(left, right) == (83, 150)
    assert time_similarity(left, left) == (100, 180)


@pytest.mark.parametrize("right", [[TimeSlot(1, 1320, 1440)], [TimeSlot(2, 1140, 1320)]])
def test_adjacent_or_different_weekday_slots_have_zero_overlap(right):
    assert time_similarity(cpp().time_slots, right) == (0, 0)


def test_shorter_schedule_fully_covered_scores_100_and_js_rounding():
    assert time_similarity([TimeSlot(7, 0, 1440)], [TimeSlot(7, 60, 120)]) == (100, 60)
    assert round_score(82.5) == 83
    assert round_score(1000) == 100


@pytest.mark.parametrize("stage,score", [("强化", 100), ("基础", 70), ("入门", 40), (None, 50)])
def test_stage_distance(stage, score):
    b = cpp()
    b.stage = stage
    assert calculate_match(cpp(), b)["dimensions"]["level"] == score
