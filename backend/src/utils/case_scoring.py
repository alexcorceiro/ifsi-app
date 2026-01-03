from typing import List, Dict, Any


def compute_case_score(steps: List[Dict[str, Any]], answers: List[Dict[str, Any]]) -> float:
    by_step = {a["step_id"]: a for a in answers}

    graded_steps = [s for s in steps if s.get("step_type") in ("MCQ","DECISION")]
    if not graded_steps:
        return 0.0
    
    correct = 0
    for s in graded_steps:
        a = by_step.get(s["id"])
        if a and a.get("is_correct"):
            correct += 1
    
    return round((correct / len(graded_steps)) * 100, 2)