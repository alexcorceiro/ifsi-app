from database.connection import get_db_connection, release_db_connection
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
import fitz 
from psycopg2.extras import RealDictCursor
import traceback, psycopg2
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Any, Dict, Literal, Tuple
import re
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

from utils.course import _inspect_pdf_type, _parse_bool, ingest_pdf_to_db, get_ue_id_from_code, extract_images, manual_slide_media, extract_text_filtered_from_bytes, get_embedded_image_rects_by_page



SortField = Literal["updated_at", "created_at", "title"]
SortOrder = Literal["asc", "desc"]


# Helper pour la lecture des fichiers
async def _read_upload_bytes_any(uf: Any) -> bytes:
    if hasattr(uf, "read") and callable(uf.read):
        data = await uf.read()
        try:
            await uf.seek(0)
        except Exception:
            pass
        return data
    f = getattr(uf, "file", None)
    if f and hasattr(f, "read"):
        pos = None
        try:
            pos = f.tell()
        except Exception:
            pos = None
        data = f.read()
        try:
            if pos is not None:
                f.seek(pos)
        except Exception:
            pass
        return data
    return b""

# Création d'un cours
async def create_course(
    request: Request,
    file: UploadFile = File(...),

    # Métadonnées
    title: Optional[str] = Form(None),
    ue_code: Optional[str] = Form(None),
    desc: Optional[str] = Form(None),
    semester: Optional[int] = Form(None),
    ects: Optional[float] = Form(None),
    year: Optional[int] = Form(None),

    # Flags
    create_course: Optional[str] = Form("true"),
    create_sections: Optional[str] = Form("true"),
    no_course: Optional[str] = Form(None),
    no_sections: Optional[str] = Form(None),

    # Forçage slide
    slide_mode: Optional[str] = Form(None),
):
    conn = None
    try:
        # ----------------------------
        # 0) Flags cohérents
        # ----------------------------
        cc = _parse_bool(create_course, default=True)
        cs = _parse_bool(create_sections, default=True)
        nc = _parse_bool(no_course, default=None)
        ns = _parse_bool(no_sections, default=None)
        if nc is not None:
            cc = not nc
        if ns is not None:
            cs = not ns

        # ----------------------------
        # 1) Lecture du PDF
        # ----------------------------
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Fichier PDF vide ou non reçu.")

        # ----------------------------
        # 2) Détection slide/classic + doc_mode
        # ----------------------------
        info = _inspect_pdf_type(pdf_bytes)
        force_slide = _parse_bool(slide_mode, default=None)

        slide_ratio = float(info.get("slide_ratio", 0.0) or 0.0)
        mean_ar = float(info.get("mean_aspect_ratio", 0.0) or 0.0)
        mean_words = float(info.get("mean_words_per_page", 0.0) or 0.0)
        mean_draws = float(info.get("mean_drawings_per_page", 0.0) or 0.0)

        if force_slide is True:
            slide_mode_flag = True
        elif force_slide is False:
            slide_mode_flag = False
        else:
            is_slide_strong = (
                slide_ratio >= 0.60 and
                mean_ar >= 1.35 and
                mean_words <= 120 and
                mean_draws >= 4
            )
            is_classic_strong = (
                slide_ratio <= 0.20 and
                mean_ar <= 1.15 and
                mean_words >= 160 and
                mean_draws <= 4
            )
            if is_slide_strong:
                slide_mode_flag = True
            elif is_classic_strong:
                slide_mode_flag = False
            else:
                # par défaut: CLASSIC (prudent)
                slide_mode_flag = False

        doc_mode = "SLIDE" if slide_mode_flag else "CLASSIC"

        # ----------------------------
        # 3) ue_id (cas C : on ASSIGNE)
        # ----------------------------
        ue_id = None
        if cc:
            if not ue_code or not ue_code.strip():
                raise HTTPException(status_code=422, detail="ue_id requis quand create_course=true")

            ue_id = get_ue_id_from_code(ue_code)  # ✅ cas C
            print("DEBUG ue_code =", ue_code, "| ue_id =", ue_id)

        # ----------------------------
        # 4) Connexion DB (jamais None)
        # ----------------------------
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Connexion DB impossible (conn=None)")

        # ----------------------------
        # 5) Images manuelles (optionnel)
        #    Postman: img_p3, img_p5, img_p13 ...
        # ----------------------------
        form = await request.form()
        pat = re.compile(r"^img_p(\d+)(?:_(\d+))?$")
        manual_slide_media: List[Tuple[int, bytes, str]] = []

        for key, val in form.items():
            m = pat.match(str(key))
            if not m:
                continue
            if not hasattr(val, "filename") or not hasattr(val, "read"):
                continue
            page_no = int(m.group(1))
            idx = int(m.group(2)) if m.group(2) else 1

            img_bytes = await val.read()
            try:
                await val.seek(0)
            except Exception:
                pass

            if img_bytes:
                tag = f"img_p{page_no}" if idx == 1 else f"img_p{page_no}_{idx}"
                caption = f"{tag} | {val.filename}" if getattr(val, "filename", None) else tag
                manual_slide_media.append((page_no, img_bytes, caption))

        manual_slide_media.sort(key=lambda t: (t[0], t[2]))

        # ----------------------------
        # 6) Ingestion (avec hooks)
        # ----------------------------
        res = ingest_pdf_to_db(
            pdf_bytes=pdf_bytes,
            conn=conn,
            original_filename=file.filename,
            course_title=title,
            ue_id=ue_id,
            description=desc or "",
            semester=semester,
            ects=ects,
            year=year,
            create_course=cc,
            create_sections=cs,
            doc_mode=doc_mode,
            slide_mode=slide_mode_flag,
            manual_slide_media=manual_slide_media,

            # hooks indispensables
            extract_text_filtered_from_bytes=extract_text_filtered_from_bytes,
            extract_images=extract_images,
            get_embedded_image_rects_by_page=get_embedded_image_rects_by_page,
        )

        return JSONResponse({
            "ok": True,
            "doc_mode": doc_mode,
            "ue_id": ue_id,
            "source_id": res.source_id,
            "course_id": res.course_id,
            "version_id": res.version_id,
            "pages_pdf": res.total_pages_pdf,
            "pages_db": res.total_pages_db,
            "images_db": res.total_images_db,
            "manual_images_received": len(manual_slide_media),
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        
async def inspect_pdf_type_endpoint(file: UploadFile = File(...)):
   
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Fichier PDF vide ou non reçu.")

    info = _inspect_pdf_type(pdf_bytes)

    info.update({
        "filename": file.filename,
        "size_bytes": len(pdf_bytes),
    })

    return JSONResponse(info)


def get_all_courses():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.code,
                    c.title,
                    c.description,
                    c.order_no,
                    c.doc_mode,
                    c.created_at,
                    c.updated_at,
                    u.code  AS ue_code,
                    u.title AS ue_title,
                    u.year_no,
                    u.sem_no,
                    u.ects  AS ue_ects,
                    COUNT(DISTINCT cv.id) AS versions_count,
                    COUNT(DISTINCT cs.source_id) AS sources_count
                FROM academics.courses c
                JOIN academics.ue u ON u.id = c.ue_id
                LEFT JOIN academics.course_versions cv ON cv.course_id = c.id
                LEFT JOIN academics.course_sources cs ON cs.course_id = c.id
                GROUP BY c.id, u.id
                ORDER BY c.updated_at DESC, c.id DESC
            """)
            return cur.fetchall()
    finally:
        conn.close()


def get_course_by_id(course_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.code,
                    c.title,
                    c.description,
                    c.order_no,
                    c.doc_mode,
                    c.published_version_id,
                    c.created_at,
                    c.updated_at,
                    u.id    AS ue_id,
                    u.code  AS ue_code,
                    u.title AS ue_title,
                    u.year_no,
                    u.sem_no,
                    u.ects  AS ue_ects
                FROM academics.courses c
                JOIN academics.ue u ON u.id = c.ue_id
                WHERE c.id = %s
            """, (course_id,))
            course = cur.fetchone()
            if not course:
                raise HTTPException(status_code=404, detail="Course introuvable")

            cur.execute("""
                SELECT id, version_label, status, created_at, updated_at
                FROM academics.course_versions
                WHERE course_id = %s
                ORDER BY created_at DESC
            """, (course_id,))
            versions = cur.fetchall()

            cur.execute("""
                SELECT
                    cs.source_id,
                    cs.version_id,
                    cs.role,
                    cs.doc_mode,
                    cs.images_policy,
                    cs.is_primary,
                    s.title AS source_title,
                    s.year  AS source_year,
                    s.created_at AS source_created_at
                FROM academics.course_sources cs
                JOIN academics.sources s ON s.id = cs.source_id
                WHERE cs.course_id = %s
                ORDER BY cs.is_primary DESC, cs.created_at DESC
            """, (course_id,))
            sources = cur.fetchall()

            return {
                "course": course,
                "versions": versions,
                "sources": sources,
            }
    finally:
        conn.close()

async def get_course_versions(course_id: int):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM academics.course_versions
                        WHERE course_id = %s
                        ORDER BY created_at DESC
            """,(course_id,))
            return {"items":cur.fetchall()}
    except Exception:
        raise HTTPException("aucun donnée")
    
async def get_course_sources(course_id: int, version_id: Optional[int] = Query(None)):
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        cs.id AS course_source_id,
                        cs.course_id,
                        cs.version_id,
                        cs.source_id,
                        cs.role,
                        cs.doc_mode,
                        cs.images_policy,
                        cs.is_primary,
                        cs.created_at,

                        s.title AS source_title,
                        s.year  AS source_year,
                        s.doc_mode AS source_doc_mode,
                        s.md5   AS source_md5
                    FROM academics.course_sources cs
                    JOIN academics.sources s ON s.id = cs.source_id
                    WHERE cs.course_id = %s
                    ORDER BY cs.created_at DESC
                """, (course_id,))
                rows = cur.fetchall()

                if not rows:
                    raise HTTPException(status_code=404, detail="Aucune source trouvée pour ce cours")

                return {"course_id": course_id, "items": rows}

        finally:
            release_db_connection(conn)
    
async def update_course(
    course_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    doc_mode: Optional[str] = Form(None),
    order_no: Optional[int] = Form(None),
):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            fields = []
            params: Dict[str, Any] = {"id": course_id}

            if title is not None:
                fields.append("title = %(title)s")
                params["title"] = title
            if description is not None:
                fields.append("description = %(description)s")
                params["description"] = description
            if doc_mode is not None:
                fields.append("doc_mode = %(doc_mode)s")
                params["doc_mode"] = doc_mode.strip().upper()
            if order_no is not None:
                fields.append("order_no = %(order_no)s")
                params["order_no"] = int(order_no)

            if not fields:
                raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

            sql = f"""
                UPDATE academics.courses
                SET {", ".join(fields)}, updated_at = NOW()
                WHERE id = %(id)s
                RETURNING id, ue_id, code, title, description, order_no, doc_mode, updated_at
            """
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Course introuvable")

        conn.commit()
        return row

    except HTTPException:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


async def delete_course(course_id: int):
    conn = None
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM academics.courses WHERE id = %s RETURNING id", (course_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Course introuvable")
            
            conn.commit()
            return {"ok": True , "deleted_course_id": course_id}
    except Exception:
        raise HTTPException("aucune donnée")

async def debug_last_courses(limit: int = Query(5, ge=1, le=50)):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  c.id AS course_id,
                  c.title,
                  COUNT(DISTINCT cv.id) AS versions,
                  COUNT(DISTINCT cs.source_id) AS sources,
                  COUNT(DISTINCT sp.id) AS pages
                FROM academics.courses c
                LEFT JOIN academics.course_versions cv ON cv.course_id = c.id
                LEFT JOIN academics.course_sources cs ON cs.course_id = c.id
                LEFT JOIN academics.source_pages sp ON sp.source_id = cs.source_id
                GROUP BY c.id, c.title
                ORDER BY c.id DESC
                LIMIT %s
            """, (limit,))
            return {"items": cur.fetchall()}
    finally:
        if conn:
            try: conn.close()
            except Exception: pass



async def delete_course_version(course_id: int, version_id: int):
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM academics.course_versions
                            WHERE id = %s AND course_id = %s
                """,(version_id, course_id))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="version introuvable")
                
                cur.execute("""
                    SELECT COUNT(*)
                            FROM academics.course_versions
                            WHERE course_id = %s
                """(course_id, ))
                nb_versions = cur.fetchone()[0]

                if nb_versions <= 1:
                 raise HTTPException(
                    status_code=400,
                    detail="Impossible de supprimer la seule version restante du cours"
                )

        
            cur.execute("""
                DELETE FROM academics.course_versions
                WHERE id = %s
            """, (version_id,))

            conn.commit()
            return {"ok": True, "deleted_version_id": version_id}

        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            release_db_connection(conn)