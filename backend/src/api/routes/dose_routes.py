from fastapi import APIRouter
from api.controller.dose_controller import (
    calculate, list_calculations, get_calculation, update_calculation, delete_calculation
)

router = APIRouter(prefix="/dose",  tags=["dose"])

router.post("/calculate")(calculate)
router.get("/calculations")(list_calculations)
router.get("/calculations/{calc_id}")(get_calculation)
router.patch("/calculations/{clac_id}")(update_calculation)
router.delete("/calculations/{clac_id}")(delete_calculation)