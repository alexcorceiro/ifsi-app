from fastapi import APIRouter
from api.controller.case_controller import ( list_cases, get_case,start_case, get_attempt_state, answer_step)

router = APIRouter(prefix="/training", tags=["training-cases"])

router.get("/cases")(list_cases)
router.get("/cases/{case_id}")(get_case)
router.post("/cases/{case_id}/start/")(start_case)

router.get("/case-attempts/{attempt_id}")(get_attempt_state)
router.post("/case-attempts/{attempt_id}/steps/{step_id}/answer")(answer_step)