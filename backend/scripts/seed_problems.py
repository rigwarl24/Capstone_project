"""Load coding problems and their test cases from database/problems.json into MySQL.

Run from the backend folder:

    python -m scripts.seed_problems            # check the file, then load it
    python -m scripts.seed_problems --check    # only check the file (no database)

Safe to run many times: a problem with the same "slug" is updated (and its test
cases replaced) instead of being added twice. Problems are never deleted.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

PROBLEMS_FILE = Path(__file__).resolve().parent.parent / "database" / "problems.json"

REQUIRED_FIELDS = ("slug", "title", "difficulty", "game_mode", "function_name",
                   "description", "starter_code", "tests")
DIFFICULTIES = {"Easy", "Medium", "Hard"}
GAME_MODES = {"speed_duel", "bug_hunt", "optimization"}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MIN_TESTS, MAX_TESTS = 5, 10


def _normalize(value):
    """Make Python results comparable with JSON values (tuples -> lists, etc.)."""
    return json.loads(json.dumps(value))


def _run_solution(code: str, function_name: str, args: list):
    namespace: dict = {}
    exec(code, namespace)  # code written by the problem author, not by players
    return namespace[function_name](*copy.deepcopy(args))


def validate_problem(problem: dict, position: int) -> list[str]:
    """Return a list of error messages for one problem (empty list = valid)."""
    label = f"Problem #{position} ({problem.get('slug', 'no slug')})"
    errors = [f"{label}: missing field '{f}'" for f in REQUIRED_FIELDS if f not in problem]
    if errors:
        return errors

    if not SLUG_PATTERN.match(problem["slug"]) or len(problem["slug"]) > 100:
        errors.append(f"{label}: slug must be lowercase words joined by '-', e.g. 'two-sum'")
    if len(problem["title"]) > 150:
        errors.append(f"{label}: title is longer than 150 characters")
    if problem["difficulty"] not in DIFFICULTIES:
        errors.append(f"{label}: difficulty must be one of {sorted(DIFFICULTIES)}")
    if problem["game_mode"] not in GAME_MODES:
        errors.append(f"{label}: game_mode must be one of {sorted(GAME_MODES)}")
    if not problem["function_name"].isidentifier():
        errors.append(f"{label}: function_name is not a valid Python name")
    elif f"def {problem['function_name']}(" not in problem["starter_code"]:
        errors.append(f"{label}: starter_code must define {problem['function_name']}(...)")
    for limit in ("time_limit_ms", "memory_limit_mb"):
        value = problem.get(limit, 1)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"{label}: {limit} must be a positive whole number")

    tests = problem["tests"]
    if not isinstance(tests, list) or not MIN_TESTS <= len(tests) <= MAX_TESTS:
        errors.append(f"{label}: needs {MIN_TESTS} to {MAX_TESTS} tests")
        return errors
    for i, test in enumerate(tests, start=1):
        if not isinstance(test, dict) or not {"input", "expected", "hidden"} <= test.keys():
            errors.append(f"{label}: test {i} needs 'input', 'expected' and 'hidden'")
        elif not isinstance(test["input"], list):
            errors.append(f"{label}: test {i} 'input' must be a list of arguments")
        elif not isinstance(test["hidden"], bool):
            errors.append(f"{label}: test {i} 'hidden' must be true or false")
    if errors:
        return errors
    if not any(t["hidden"] for t in tests) or all(t["hidden"] for t in tests):
        errors.append(f"{label}: needs at least one visible and one hidden test")

    # If a reference solution is given, check every expected answer with it.
    solution = problem.get("reference_solution")
    if solution:
        for i, test in enumerate(tests, start=1):
            try:
                got = _normalize(_run_solution(solution, problem["function_name"], test["input"]))
            except Exception as error:  # report any crash in the reference solution
                errors.append(f"{label}: reference solution crashed on test {i}: {error!r}")
                continue
            if got != test["expected"]:
                errors.append(f"{label}: test {i} expects {test['expected']!r} "
                              f"but the reference solution returns {got!r}")

    # A Bug Hunt starter must really be buggy (fail at least one test).
    if problem["game_mode"] == "bug_hunt":
        def starter_passes(test):
            try:
                result = _run_solution(problem["starter_code"], problem["function_name"],
                                       test["input"])
                return _normalize(result) == test["expected"]
            except Exception:
                return False
        if all(starter_passes(t) for t in tests):
            errors.append(f"{label}: bug_hunt starter_code already passes every test")
    return errors


def load_problems() -> list[dict]:
    with open(PROBLEMS_FILE, encoding="utf-8") as file:
        problems = json.load(file)
    if not isinstance(problems, list):
        raise SystemExit("problems.json must contain a list [ ... ] of problems")
    return problems


def validate_all(problems: list[dict]) -> list[str]:
    errors = []
    slugs = [p.get("slug") for p in problems]
    for slug in {s for s in slugs if slugs.count(s) > 1}:
        errors.append(f"Duplicate slug '{slug}' appears more than once")
    for position, problem in enumerate(problems, start=1):
        errors.extend(validate_problem(problem, position))
    return errors


def seed(problems: list[dict]) -> tuple[int, int, int]:
    """Insert or update every problem in one transaction. Returns (created, updated, tests)."""
    from sqlalchemy import text

    from app.database import engine

    created = updated = test_count = 0
    with engine.begin() as db:  # commits at the end, or rolls back everything on error
        for p in problems:
            values = {
                "slug": p["slug"], "title": p["title"], "description": p["description"],
                "difficulty": p["difficulty"], "game_mode": p["game_mode"],
                "function_name": p["function_name"], "starter_code": p["starter_code"],
                "time_limit_ms": p.get("time_limit_ms", 2000),
                "memory_limit_mb": p.get("memory_limit_mb", 128),
            }
            row = db.execute(text("SELECT id FROM problems WHERE slug = :slug"),
                             {"slug": p["slug"]}).first()
            if row is None:
                result = db.execute(text("""
                    INSERT INTO problems (slug, title, description, difficulty, game_mode,
                                          function_name, starter_code, time_limit_ms,
                                          memory_limit_mb)
                    VALUES (:slug, :title, :description, :difficulty, :game_mode,
                            :function_name, :starter_code, :time_limit_ms, :memory_limit_mb)
                """), values)
                problem_id = result.lastrowid
                created += 1
            else:
                problem_id = row.id
                db.execute(text("""
                    UPDATE problems
                    SET title = :title, description = :description, difficulty = :difficulty,
                        game_mode = :game_mode, function_name = :function_name,
                        starter_code = :starter_code, time_limit_ms = :time_limit_ms,
                        memory_limit_mb = :memory_limit_mb
                    WHERE id = :id
                """), {**values, "id": problem_id})
                db.execute(text("DELETE FROM testcases WHERE problem_id = :id"),
                           {"id": problem_id})
                updated += 1

            for order, test in enumerate(p["tests"], start=1):
                db.execute(text("""
                    INSERT INTO testcases (problem_id, input_data, expected_output,
                                           is_hidden, order_index)
                    VALUES (:problem_id, :input_data, :expected_output, :is_hidden, :order_index)
                """), {
                    "problem_id": problem_id,
                    "input_data": json.dumps(test["input"]),
                    "expected_output": json.dumps(test["expected"]),
                    "is_hidden": test["hidden"],
                    "order_index": order,
                })
                test_count += 1
    return created, updated, test_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Load problems.json into the database.")
    parser.add_argument("--check", action="store_true",
                        help="only check problems.json, do not touch the database")
    args = parser.parse_args()

    problems = load_problems()
    errors = validate_all(problems)
    if errors:
        print(f"Found {len(errors)} problem(s) in {PROBLEMS_FILE.name}:")
        for error in errors:
            print("  -", error)
        print("Nothing was loaded into the database.")
        sys.exit(1)

    total_tests = sum(len(p["tests"]) for p in problems)
    print(f"OK: {len(problems)} problems and {total_tests} tests are valid.")
    if args.check:
        return

    created, updated, test_count = seed(problems)
    print(f"Database updated: {created} created, {updated} updated, {test_count} tests loaded.")


if __name__ == "__main__":
    main()