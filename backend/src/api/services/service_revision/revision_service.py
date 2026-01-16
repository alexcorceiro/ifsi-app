from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from core.revision_repo import RevisionRepo

def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return dict(zip(cols, row))


def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]



     
class RevisionService:
    def __init__(self, conn) :
        self.conn = conn


    
    def render_sheet_blocks(self, sheet_id: int) -> Dict[str, Any]:
       
        with self.conn.cursor() as cur:
            # Sheet
            cur.execute(
                """
                SELECT
                  id, course_id, version_id, target_type, target_id,
                  title, status, content_md, created_at, updated_at
                FROM revision.revision_sheets
                WHERE id=%s
                """,
                (sheet_id,),
            )
            sheet = _fetchone_dict(cur)
            if sheet is None:
                raise ValueError("sheet not found")

            # Items
            cur.execute(
                """
                SELECT
                  id, sheet_id, item_type, position, title, body_md,
                  source_id, page_start, page_end, created_at
                FROM revision.revision_sheet_items
                WHERE sheet_id=%s
                ORDER BY position ASC, id ASC
                """,
                (sheet_id,),
            )
            items = _fetchall_dict(cur)

            # Assets
            cur.execute(
                """
                SELECT
                  id, sheet_id, asset_type, source_id, file_url,
                  anchor, anchor_item_id,
                  page_no, x, y, w, h, z_index,
                  caption_md, meta, created_at
                FROM revision.sheet_assets
                WHERE sheet_id=%s
                ORDER BY page_no ASC, z_index ASC, id ASC
                """,
                (sheet_id,),
            )
            assets = _fetchall_dict(cur)

        # Groupement items
        blocks: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            t = it.get("item_type") or "BULLET"
            blocks.setdefault(t, []).append(it)

        # Groupement assets
        assets_by_page: Dict[str, List[Dict[str, Any]]] = {}
        for a in assets:
            p = str(a.get("page_no") or 1)
            assets_by_page.setdefault(p, []).append(a)

        return {
            "sheet_id": sheet["id"],
            "sheet": sheet,
            "items": items,
            "assets": assets,
            "blocks": blocks,
            "assets_by_page": assets_by_page,
        }

    @staticmethod
    def _validate_sheet_target(payload: dict) -> None:
        has_target = payload.get("target_type") is not None and payload.get("target_id") is not None
        has_course = payload.get("course_id") is not None
        if not (has_target or has_course):
            raise ValueError("sheet must have target_type+target_id or course_id")
    
    @staticmethod
    def _validate_asset_anchor(payload: Dict[str, Any]) -> None:
        if payload.get("anchor") == "ITEM" and not payload.get("anchor_item_id"):
            raise ValueError("anchor_item_id required when anchor=ITEM")
        if not payload.get("source_id") and not payload.get("file_url"):
            raise ValueError("asset must provide source_id or file_url")
        
    def create_sheet(self, payload: Dict[str, Any]) -> int:
        self._validate_sheet_target(payload)
        with self.conn.cursor() as cur:
            return RevisionRepo.create_sheet(cur, payload)
        
    def list_sheets(
        self,
        *,
        course_id: Optional[int],
        version_id: Optional[int],
        target_type: Optional[str],
        target_id: Optional[int],
        status: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            return RevisionRepo.list_sheets(
                cur,
                course_id=course_id,
                version_id=version_id,
                target_type=target_type,
                target_id=target_id,
                status=status,
                limit=limit,
                offset=offset,
            )   

    def get_sheet(self, sheet_id: int):
     with self.conn.cursor() as cur:
        sheet = RevisionRepo.get_sheet(cur, sheet_id)
        if not sheet:
            raise ValueError("sheet not found")
        return sheet

    def get_sheet_full(self, sheet_id: int) -> Dict[str, Any]:

         with self.conn.cursor() as cur:
            sheet = RevisionRepo.get_sheet(cur, sheet_id)   # objet dict
            items = RevisionRepo.list_items(cur, sheet_id)  # list
            assets = RevisionRepo.list_assets(cur, sheet_id) # list

            return {"sheet": sheet, "items": items, "assets": assets}
         
    
    def update_sheet(self , sheet_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
       touches_target = any(k in payload for k in ("target_type", "target_id", "course_id"))
       if touches_target:
            existing = self.get_sheet(sheet_id)
            merged = {**existing, **{k: v for k, v in payload.items() if v is not None}}
            self._validate_sheet_target(merged)

       with self.conn.cursor() as cur:
            updated = RevisionRepo.update_sheet(cur, sheet_id, payload)
            if updated is None:
                return self.get_sheet(sheet_id)
            return updated
        
    def delete_sheet(self, sheet_id: int) -> bool:
        with self.conn.cursor() as cur:
            ok = RevisionRepo.delete_sheet(cur, sheet_id)
            if not ok:
                raise ValueError("sheet not found")
            return True
        
    def add_item(self, payload: Dict[str, Any]) -> int:
        sheet_id = payload["sheet_id"]
        # vérifie sheet existe
        _ = self.get_sheet(sheet_id)
        with self.conn.cursor() as cur:
            return RevisionRepo.create_item(cur, payload)

    def list_items(self, sheet_id: int) -> List[Dict[str, Any]]:
        _ = self.get_sheet(sheet_id)
        with self.conn.cursor() as cur:
            return RevisionRepo.list_items(cur, sheet_id)

    def delete_item(self, item_id: int) -> bool:
        with self.conn.cursor() as cur:
            ok = RevisionRepo.delete_item(cur, item_id)
            if not ok:
                raise ValueError("item not found")
            return True
        
    def add_asset(self, payload: Dict[str, Any]) -> int:
        sheet_id = payload["sheet_id"]
        _ = self.get_sheet(sheet_id)

        self._validate_asset_anchor(payload)

        # si anchor_item_id donné, on peut vérifier que l'item appartient au sheet
        anchor_item_id = payload.get("anchor_item_id")
        if payload.get("anchor") == "ITEM" and anchor_item_id:
            items = self.list_items(sheet_id)
            if not any(int(i["id"]) == int(anchor_item_id) for i in items):
                raise ValueError("anchor_item_id does not belong to sheet")

        with self.conn.cursor() as cur:
            return RevisionRepo.create_asset(cur, payload)

    def list_assets(self, sheet_id: int) -> List[Dict[str, Any]]:
        _ = self.get_sheet(sheet_id)
        with self.conn.cursor() as cur:
            return RevisionRepo.list_assets(cur, sheet_id)

    def delete_asset(self, asset_id: int) -> bool:
        with self.conn.cursor() as cur:
            ok = RevisionRepo.delete_asset(cur, asset_id)
            if not ok:
                raise ValueError("asset not found")
            return True
        
    def render_sheet_pages(self, sheet_id: int) -> Dict[str, Any]:
        data = self.render_sheet_blocks(sheet_id)

        sheet: Dict[str, Any] = data["sheet"]
        blocks: Dict[str, List[Dict[str, Any]]] = data.get("blocks") or {}
        assets_by_page: Dict[str, List[Dict[str, Any]]] = data.get("assets_by_page") or {}

        # pages présentes selon assets, sinon au moins 1
        page_nos: List[int] = []
        for k in assets_by_page.keys():
            try:
                page_nos.append(int(k))
            except Exception:
                continue

        max_page = max(page_nos) if page_nos else 1

        default_layout: Dict[str, Any] = {
            "format": "A4",
            "unit": "px",
            "width": 794,
            "height": 1123,
            "margin": 24,
        }

        pages: List[Dict[str, Any]] = []
        for p in range(1, max_page + 1):
            pages.append(
                {
                    "page_no": p,
                    "blocks": blocks,
                    "assets": assets_by_page.get(str(p), []),
                    "layout": default_layout,
                }
            )

        return {
            "sheet_id": sheet["id"],
            "title": sheet.get("title"),
            "status": sheet.get("status"),
            "page_count": max_page,
            "pages": pages,
        }