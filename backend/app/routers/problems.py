"""Problem endpoints: public view for players, full view (with hidden tests) for the engine."""
import json

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from ..dependencies import DbConnection, InternalOnly
from ..schemas import ProblemPublic, ProblemWithTests

router = APIRouter(prefix="/api/problems", tags=["Problems"])

PROBLEM_COLUMNS = """
    id, slug, title, description, difficulty, game_mode, function_name,
    starter_code, time_limit_ms, memory_limit_mb
"""


def load_problem(db: DbConnection, problem_id: int) -> tuple[dict, list[dict]]:
    """Return (problem, tests) or reply 404."""
    problem = db.execute(
        text(f"SELECT {PROBLEM_COLUMNS} FROM problems WHERE id = :id AND is_active"),
        {"id": problem_id},
    ).mappings().first()
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

    rows = db.execute(
        text("SELECT input_data, expected_output, is_hidden FROM testcases "
             "WHERE problem_id = :id ORDER BY order_index, id"),
        {"id": problem_id},
    ).all()
    tests = [{"input": json.loads(r.input_data), "expected": json.loads(r.expected_output),
              "hidden": bool(r.is_hidden)} for r in rows]
    return dict(problem), tests


@router.get("/{problem_id}", response_model=ProblemPublic)
def get_problem(problem_id: int, db: DbConnection):
    """Problem as shown to players. Hidden tests are NOT included."""
    problem, tests = load_problem(db, problem_id)
    visible = [{"input": t["input"], "expected": t["expected"]} for t in tests if not t["hidden"]]
    return {**problem, "visible_tests": visible}


@router.get("/{problem_id}/all-tests", response_model=ProblemWithTests,
            dependencies=[InternalOnly])
def get_problem_with_all_tests(problem_id: int, db: DbConnection):
    """Internal: problem with visible AND hidden tests (needs the X-Internal-Key header)."""
    problem, tests = load_problem(db, problem_id)
    visible = [{"input": t["input"], "expected": t["expected"]} for t in tests if not t["hidden"]]
    return {**problem, "visible_tests": visible, "all_tests": tests}