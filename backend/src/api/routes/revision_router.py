from fastapi import APIRouter


from api.controller.revision_controller import(
    create_sheet,
    list_sheets,
    get_sheet,
    get_sheet_full,
    render_sheet,
    update_sheet,
    delete_sheet,
    add_asset,
    list_items,
    delete_item,
    add_item,
    list_assets,
    delete_asset,
    render_sheet_pages
)

from api.controller.revision_srs_controller import (
    create_flashcard,
    list_flashcards,
    update_flashcard,
    delete_flashcard,
    srs_due,
    srs_review,
    srs_stats
)

router = APIRouter(prefix="/revision"  , tags=["revision"])


router.post("/sheets")(create_sheet)
router.get("/sheets")(list_sheets)
router.get("/sheets/{sheet_id}")(get_sheet)
router.get("/sheets/{sheet_id}/full")(get_sheet_full)
router.get("/sheets/{sheet_id}/render")(render_sheet)
router.get("/sheets/{sheet_id}/render/pages")(render_sheet_pages)
router.patch("/sheets/{sheet_id}")(update_sheet)
router.delete("/sheets/{sheet_id}")(delete_sheet)


router.post("/items")(add_item)
router.get("/sheets/{sheet_id}/items")(list_items)
router.delete("/items/{item_id}")(delete_item)

router.post("/assets")(add_asset)
router.get("/sheets/{sheet_id}/assets")(list_assets)
router.delete("/assets/{asset_id}")(delete_asset)


router.post("/flashcards")(create_flashcard)
router.get("/flashcards")(list_flashcards)
router.patch("/flashcards/{flashcard_id}")(update_flashcard)
router.delete("/flaschcards/{fashcard_id}")(delete_flashcard)

router.get("/srs/due")(srs_due)
router.post("srs/review")(srs_review)
router.get("/srs/stats")(srs_stats)

