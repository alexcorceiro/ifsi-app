from fastapi import APIRouter
from api.controller.cours_controller import (create_course, get_course_by_id, get_all_courses,
                                             debug_last_courses, get_course_versions, get_course_sources,
                                             update_course,delete_course)


router = APIRouter(prefix="/courses", tags=["courses"])



router.post("")(create_course)
router.get("")(get_all_courses)
router.get("/{course_id}")(get_course_by_id)
router.get("/debug/last")(debug_last_courses)
router.get("/version/{course_id}")(get_course_versions)
router.get("/sources/{course_id}")(get_course_sources)
router.patch("/{sourse_id}")(update_course)
router.delete("{sourse_id}")(delete_course)
router.delete("/{course_id}/versions/{version_id}")