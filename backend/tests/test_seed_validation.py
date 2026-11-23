"""Tests for the problems.json checker (no database needed)."""
import copy

from scripts.seed_problems import load_problems, validate_all


def test_real_problems_file_is_valid():
    assert validate_all(load_problems()) == []


def test_wrong_expected_answer_is_caught():
    problems = copy.deepcopy(load_problems())
    problems[0]["tests"][0]["expected"] = [9, 9]
    errors = validate_all(problems)
    assert any("reference solution returns" in e for e in errors)


def test_bad_difficulty_is_caught():
    problems = copy.deepcopy(load_problems())
    problems[0]["difficulty"] = "Very Hard"
    assert any("difficulty" in e for e in validate_all(problems))


def test_too_few_tests_is_caught():
    problems = copy.deepcopy(load_problems())
    problems[0]["tests"] = problems[0]["tests"][:2]
    assert any("needs 5 to 10 tests" in e for e in validate_all(problems))


def test_duplicate_slug_is_caught():
    problems = copy.deepcopy(load_problems())
    problems.append(copy.deepcopy(problems[0]))
    assert any("Duplicate slug" in e for e in validate_all(problems))


def test_bug_hunt_without_a_bug_is_caught():
    problems = copy.deepcopy(load_problems())
    bug = next(p for p in problems if p["game_mode"] == "bug_hunt")
    bug["starter_code"] = bug["reference_solution"]
    assert any("already passes every test" in e for e in validate_all(problems))