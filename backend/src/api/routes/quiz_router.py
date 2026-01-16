from fastapi import APIRouter


from api.controller.quiz_controller import (
    create_quiz,
    list_quizzes,
    get_quiz,
    update_quiz,
    delete_quiz,
    create_item,
    list_items,
    start_attempt,
    answer_item, 
    finish_attempt
)

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


router.post("")(create_quiz)
router.get("")(list_quizzes)
router.get("/{quiz_id}")(get_quiz)
router.patch("/{quiz_id}")(update_quiz)
router.delete("/{quiz_id}")(delete_quiz)

router.post("/{quiz_id}/items")(create_item)
router.get("/{quiz_id}/items")(list_items)


router.post("/{quiz_id}/attempts")(start_attempt)
router.post("/attempts/{attempt_id}/items/{item_id}/answer")(answer_item)
router.post("/attempts/{attempt_id}/finish")(finish_attempt)