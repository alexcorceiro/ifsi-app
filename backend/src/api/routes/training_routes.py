from fastapi import APIRouter
from api.controller.training_controller import (
    create_exercise,
    list_exercises,
    get_exercise,
    submit_attempt,
    list_attempts,
    get_attempt,
)

router = APIRouter(prefix="/training", tags=["training"])

# Exercises
router.post("/exercises")(create_exercise)
router.get("/exercises")(list_exercises)
router.get("/exercises/{exercise_id}")(get_exercise)

# Attempts
router.post("/exercises/{exercise_id}/attempts")(submit_attempt)
router.get("/attempts")(list_attempts)
router.get("/attempts/{attempt_id}")(get_attempt)
