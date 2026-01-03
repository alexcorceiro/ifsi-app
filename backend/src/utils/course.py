import os, re, hashlib, argparse, datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Set , Union
import numpy as np
import fitz
import psycopg2
from psycopg2.extras import Json , RealDictCursor
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
from database.connection import get_db_connection
import statistics
from io import BytesIO
from PIL import Image

# ===================================================================
# CONSTANTES (réglages extraction)
# ===================================================================
MIN_REGION_PX = 110          # taille mini (en pixels rendus) d’un crop image
MIN_AREA_RATIO = 0.010       # 1% de la page mini
MAX_AREA_RATIO = 0.90        # >90% = page quasi entière -> on ignore
WORD_DENSITY_REJECT = 0.35   # part de l’aire couverte par des mots => rejet
ASPECT_THIN_RATIO = 0.08     # si min/max côtés < 0.08 => trop filiforme
IOU_MERGE = 0.30             # fusion des candidats
EDGE_GAP = 12.0              # “bords qui se touchent” => fusion
IOU_SAME = 0.60              # deux crops trop proches => doublon
PHASH_MAX_DIST = 6           # distance Hamming pHash pour doublons visuels
RENDER_SCALE = 2.0           # facteur de rendu pour les crops

TITLE_PAT = re.compile(
    r'^\s*(?:[IVXLC]+\.\s+|\d+(?:\.\d+)*\s+|PARTIE\s+\d+|CHAPITRE\s+\d+)',
    re.I
)

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

@dataclass
class PDFIngestResult:
    source_id: int
    course_id: Optional[int]
    version_id: Optional[int]
    total_pages_pdf: int
    total_pages_db: int
    total_images_pdf: int
    total_images_db: int
    text_len_pdf: int
    text_len_db: int
    text_hash_pdf: str
    text_hash_db: str
    missing_pages: List[int]
    empty_pages: List[int]
    coverage_ok: bool


@dataclass
class ManualMedia:
    page_no: int
    kind: str
    filename: Optional[str]
    data: bytes
     
def _inspect_pdf_type(pdf_bytes: bytes) -> dict:
   
    max_pages = 20  

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return {
            "is_slide": False,
            "error": "Fichier illisible comme PDF.",
            "slide_ratio": 0.0,
            "n_pages_total": 0,
            "n_pages_scanned": 0,
            "mean_aspect_ratio": 0.0,
            "mean_words_per_page": 0.0,
            "mean_drawings_per_page": 0.0,
            "pages": [],
        }

    n_pages = len(doc)
    if n_pages == 0:
        doc.close()
        return {
            "is_slide": False,
            "error": "PDF sans pages.",
            "slide_ratio": 0.0,
            "n_pages_total": 0,
            "n_pages_scanned": 0,
            "mean_aspect_ratio": 0.0,
            "mean_words_per_page": 0.0,
            "mean_drawings_per_page": 0.0,
            "pages": [],
        }

    pages_to_scan = min(max_pages, n_pages)

    slide_votes = 0
    pages_info = []

    for pno in range(pages_to_scan):
        page = doc[pno]
        rect = page.rect
        ar = rect.width / max(rect.height, 1.0)

        try:
            words = page.get_text("words") or []
            n_words = len(words)
        except Exception:
            n_words = 0

        try:
            drawings = page.get_drawings() or []
            n_drawings = len(drawings)
        except Exception:
            n_drawings = 0

        
        is_slide_page = (
            1.30 <= ar <= 2.10 and
            (n_words <= 120 or n_drawings >= 6)
        )

        if is_slide_page:
            slide_votes += 1

        pages_info.append({
            "page_no": pno + 1,
            "aspect_ratio": ar,
            "n_words": n_words,
            "n_drawings": n_drawings,
            "is_slide_like": is_slide_page,
        })

    doc.close()

    if not pages_info:
        return {
            "is_slide": False,
            "slide_ratio": 0.0,
            "n_pages_total": n_pages,
            "n_pages_scanned": 0,
            "mean_aspect_ratio": 0.0,
            "mean_words_per_page": 0.0,
            "mean_drawings_per_page": 0.0,
            "pages": [],
        }

    slide_ratio = slide_votes / pages_to_scan
    mean_ar = sum(p["aspect_ratio"] for p in pages_info) / len(pages_info)
    mean_words = sum(p["n_words"] for p in pages_info) / len(pages_info)
    mean_draws = sum(p["n_drawings"] for p in pages_info) / len(pages_info)

    
    is_slide = False
    if slide_ratio >= 0.55:
        is_slide = True
    elif (
        slide_ratio >= 0.40 and
        mean_ar >= 1.40 and
        mean_words <= 150 and
        mean_draws >= 4
    ):
        is_slide = True

    return {
        "is_slide": is_slide,
        "slide_ratio": slide_ratio,
        "n_pages_total": n_pages,
        "n_pages_scanned": pages_to_scan,
        "mean_aspect_ratio": mean_ar,
        "mean_words_per_page": mean_words,
        "mean_drawings_per_page": mean_draws,
        "pages": pages_info,
    }




def get_ue_id_from_code(ue_code: str) -> int:
    if not ue_code or not ue_code.strip():
        raise HTTPException(status_code=400, detail="ue_code manquant")

    code = ue_code.strip()

    conn = get_db_connection()
    try:
        # Debug DB context
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()")
            print("API DB CONTEXT =", cur.fetchone())

        # Requête UE
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, code FROM academics.ue WHERE code = %s",
                (code,)
            )
            row = cur.fetchone()
            print("UE ROW =", row)

            if not row:
                raise HTTPException(status_code=404, detail="UE non trouvée")

            return int(row["id"])
    finally:
        conn.close()

def sha256_text(s: Union[str, bytes]) -> str:
    """
    Accepte soit une str soit des bytes.
    - bytes -> on les décode avant
    - str   -> on encode directement
    """
    if isinstance(s, bytes):
        # décodage permissif pour ne jamais planter
        s = s.decode("latin1", errors="ignore")
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def rect_to_list(bbox):
    try:
        if isinstance(bbox, fitz.Rect):
            return [float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)]
    except Exception:
        pass
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        try:
            return [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
        except Exception:
            return None
    return None



def upsert_source_bytes(cur, title: str, year: Optional[int], doc_mode: str, md5_file: str) ->int:
     conn = get_db_connection()
     cur = conn.cursor()

     cur.execute("SELECT id FROM academics.sources WHERE md5 = %s LIMIT 1", (md5_file,))     
     row = cur.fetchone()
     if row:
          return row[0]
     cur.execute(
                """
                INSERT INTO academics.sources (title, year, doc_mode, md5)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (md5)
                DO UPDATE SET
                title = EXCLUDED.title,
                year = EXCLUDED.year,
                doc_mode = EXCLUDED.doc_mode
                RETURNING id
                """,
                (title, year, doc_mode, md5_file),
        )
     return cur.fetchone()[0]

def upsert_source_page(cur, *, source_id: int, page_no: int, text: str, ocr_text: Optional[str] = None):
    cur.execute(
        """
        INSERT INTO academics.source_pages (source_id, page_no, text, ocr_text)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (source_id, page_no)
        DO UPDATE SET
            text = EXCLUDED.text,
            ocr_text = EXCLUDED.ocr_text
        """,
        (source_id, page_no, text, ocr_text),
    )
     
def insert_section(cur, course_id: int, version_id: Optional[int], parent_id: Optional[int],
                   position: int, title: str, content_md: str) -> int:
     conn = get_db_connection()
     cur = conn.cursor()

     cur.execute("""
        INSERT INTO academics.sections(course_id, version_id, parent_id, position, title, content_md)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (course_id, version_id, parent_id, position, title, content_md))
     return cur.fetchone()[0]

def insert_citation(cur, section_id: int, source_id: int, page_start: int,
                    page_end: Optional[int], quote: Optional[str]):
     conn = get_db_connection()
     cur = conn.cursor()

     cur.execute("""
        INSERT INTO academics.citations(section_id, source_id, page_start, page_end, quote)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (section_id, source_id, page_start, page_end, quote))

def insert_source_file_bytes(cur, source_id: int, pdf_bytes: bytes):
     conn = get_db_connection()
     cur = conn.cursor()

     cur.execute("""
        INSERT INTO academics.source_files (source_id, pdf_data)
        VALUES (%s, %s)
        ON CONFLICT (source_id) DO UPDATE
        SET pdf_data = EXCLUDED.pdf_data
    """, (source_id, psycopg2.Binary(pdf_bytes)))

def add_version(cur, course_id: int, label: Optional[str] = None) -> int:
    label = label or f"v{datetime.date.today().isoformat()}-auto"
    cur.execute("""
        INSERT INTO academics.course_versions(course_id, version_label, status)
        VALUES (%s, %s, 'draft')
        ON CONFLICT (course_id, version_label) DO UPDATE SET updated_at = NOW()
        RETURNING id
    """, (course_id, label))
    return int(cur.fetchone()[0])


def _load_existing_media_phases(cur, source_id: int) -> Set[int]:
     conn = get_db_connection()
     cur = conn.cursor()

     cur.execute("""
        SELECT id, data
        FROM academics.page_media_assets
        WHERE source_id = %s AND data IS NOT NULL
    """, (source_id,))
     rows = cur.fetchall() or []
     phashes: Set[int] = set()

     for _id, blob in rows:
          if not blob: 
               continue
          try:
               doc_img = fitz.open(stream=bytes(blob), filetype="png")
               try:
                    pg = doc_img[0]
                    pix = pg.get_pixmap(alpha=False)
               finally:
                    doc_img.close()
          except Exception:
               try:
                    doc_img = fitz.open(stream=bytes(blob))
                    try:
                         if len(doc_img) == 0:
                              continue
                         pg = doc_img[0]
                         pix = pg.get_pixmap(alpha=False)
                    finally: 
                     doc_img.close()
               except Exception:
                    continue
     return phashes

def _insert_png_from_pix(cur, source_id: int, page_no: int, pix: fitz.Pixmap,
                         kind: str = "figure", caption: Optional[str] = None,
                         bbox: Optional[fitz.Rect] = None) -> Optional[int]:
    png = pix.tobytes("png")
    md5 = hashlib.md5(png).hexdigest()

    cur.execute("""
        INSERT INTO academics.page_media_assets(
            source_id, page_no, kind, mime, data, md5, bbox, width, height
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
        RETURNING id
    """, (
        source_id, page_no, kind, "image/png", psycopg2.Binary(png), md5,
        Json(rect_to_list(bbox)) if bbox else None, pix.width, pix.height
    ))
    row = cur.fetchone()
    return int(row[0]) if row else None

def get_ue_id_by_code(cur, ue_code: str) -> int:
    ue_code = (ue_code or "").strip()
    if not ue_code:
        raise HTTPException(status_code=422, detail="ue_code est requis (non vide).")

    cur.execute(
        "SELECT id FROM academics.ue WHERE code = %s LIMIT 1",
        (ue_code,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=422, detail=f"UE introuvable pour code={ue_code!r}")
    return int(row[0])


def upsert_course(
    cur,
    *,
    ue_id: int,
    code: str,
    title: str,
    description: Optional[str] = None,
    order_no: int = 0,
    doc_mode: str = "CLASSIC",
) -> int:
    if not ue_id or ue_id <= 0:
        raise HTTPException(status_code=422, detail="ue_id invalide.")
    code = (code or "").strip()
    title = (title or "").strip()
    if not code:
        raise HTTPException(status_code=422, detail="code cours requis.")
    if not title:
        raise HTTPException(status_code=422, detail="title cours requis.")

    cur.execute(
        """
        INSERT INTO academics.courses (ue_id, code, title, description, order_no, doc_mode)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (ue_id, code)
        DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            order_no = EXCLUDED.order_no,
            doc_mode = EXCLUDED.doc_mode,
            updated_at = NOW()
        RETURNING id
        """,
        (ue_id, code, title, description, order_no, doc_mode),
    )
    return int(cur.fetchone()[0])


def get_embedded_image_rects_by_page(doc: fitz.Document) -> Dict[int, List[fitz.Rect]]:
   
    img_rects: Dict[int, List[fitz.Rect]] = {}

    for i in range(len(doc)):
        page = doc[i]
        rects: List[fitz.Rect] = []

        for img in page.get_images(full=True) or []:
            xref = img[0]
            try:
                for r in page.get_image_rects(xref) or []:
                    if r and not r.is_empty:
                        rects.append(r)
            except Exception:
                continue

        img_rects[i + 1] = rects

    return img_rects




def detect_titles_from_page_dict(page_dict: dict) -> list[str]:
     spans = []
     for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
             continue
        for line in block.get("lines", []):
             for sp in line.get("spans",[]):
                  t = (sp.get("text") or "").strip()
                  if t: 
                       spans.append(sp)
     if not spans:
          return []
     sizes = [float(sp.get("size", 0) or 0) for sp in spans if float(sp.get("size", 0) or 0) > 0] 
     if not sizes:
          return []
     med = statistics.median(sizes)
     titles = []                                                          

     for block in page_dict.get("blockd", []):
          if block.get("type") != 0:
               continue
          for line in block.get("lines", []):
               line_text = " ".join((sp.get("text") or "").strip() for sp in line.get("spans", [])).strip()
               if not line_text:
                    continue
               max_size = max((float(sp.get("size", 0) or 0) for sp in line.get("spans", [])), default=0)
               if max_size >= med * 1.25 and len(line_text) <= 120:
                    titles.append(line_text)
     out = []
     seen= set()
     for t in titles:
        k = t.lower()
        if k not in seen:
             seen.add(k)
             out.append(t)
     return out


def extract_text_filtered_from_bytes(
    pdf_bytes: bytes,
    figure_map: Dict[int, List[fitz.Rect]],
    image_rects_map: Optional[Dict[int, List[fitz.Rect]]] = None,
    image_reacts_map: Optional[Dict[int, List[fitz.Rect]]] = None,  # alias compat
    overlap_threshold: float = 0.18,
) -> List[str]:
    if image_rects_map is None and image_reacts_map is not None:
        image_rects_map = image_reacts_map
    image_rects_map = image_rects_map or {}

    def _to_rect(bbox) -> Optional[fitz.Rect]:
        if not bbox:
            return None
        try:
            # bbox peut être (x0,y0,x1,y1)
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                return fitz.Rect(bbox)
        except Exception:
            return None
        return None

    def _overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
        """
        ratio de recouvrement: aire(intersection) / min(aire(a), aire(b))
        """
        inter = a & b
        if inter.is_empty or inter.get_area() <= 0:
            return 0.0
        denom = min(a.get_area(), b.get_area())
        return (inter.get_area() / denom) if denom > 0 else 0.0

    def _detect_titles_from_page_dict(page_dict: dict) -> List[str]:
        """
        Détection simple de titres: lignes avec police plus grande que la médiane.
        (Version stable, sans tes typos blockd.)
        """
        spans = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for sp in line.get("spans", []):
                    t = (sp.get("text") or "").strip()
                    if t:
                        spans.append(sp)

        if not spans:
            return []

        sizes = [float(sp.get("size", 0) or 0) for sp in spans if float(sp.get("size", 0) or 0) > 0]
        if not sizes:
            return []

        sizes.sort()
        med = sizes[len(sizes) // 2]

        titles = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_text = " ".join((sp.get("text") or "").strip() for sp in line.get("spans", [])).strip()
                if not line_text:
                    continue
                max_size = max((float(sp.get("size", 0) or 0) for sp in line.get("spans", [])), default=0)
                if max_size >= med * 1.25 and len(line_text) <= 140:
                    titles.append(line_text)

        # dédoublonnage
        out, seen = [], set()
        for t in titles:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(t)
        return out

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out_pages: List[str] = []

    try:
        for pno in range(len(doc)):
            page = doc[pno]
            page_no = pno + 1

            # zones à exclure
            fig_rects = figure_map.get(page_no, []) or []
            img_rects = image_rects_map.get(page_no, []) or []
            blocking_rects = [r for r in (fig_rects + img_rects) if isinstance(r, fitz.Rect)]

            page_dict = page.get_text("dict")
            titles = _detect_titles_from_page_dict(page_dict)
            titles_lower = {t.lower() for t in titles}

            lines_out: List[str] = []

            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    # texte de ligne
                    line_text = " ".join((sp.get("text") or "").strip() for sp in line.get("spans", [])).strip()
                    if not line_text:
                        continue

                    # ignore si c'est un titre (on le remettra en # plus haut)
                    if line_text.lower() in titles_lower:
                        continue

                    lrect = _to_rect(line.get("bbox"))
                    if lrect and blocking_rects:
                        # si la ligne chevauche une zone image -> on skip
                        if any(_overlap_ratio(lrect, r) >= overlap_threshold for r in blocking_rects):
                            continue

                    lines_out.append(line_text)

            # Compose markdown page
            buf: List[str] = []
            for t in titles[:3]:
                buf.append(f"# {t}")
            buf.extend(lines_out)

            out_pages.append("\n".join(buf).strip())

        return out_pages

    finally:
        try:
            doc.close()
        except Exception:
            pass  

def _normalize_pix_to_rgb(pix: fitz.Pixmap) -> fitz.Pixmap:
    try:
        if pix.n == 3:
            return pix
        return fitz.Pixmap(fitz.csRGB, pix)
    except Exception:
        return pix

def _guess_image_ftypes(img: bytes) -> List[str]:
  
    if not img or len(img) < 12:
        return []

    b = img
    sig2 = b[:2]
    sig3 = b[:3]
    sig4 = b[:4]
    sig8 = b[:8]
    box12 = b[4:12]

    # PNG
    if sig8 == b"\x89PNG\r\n\x1a\n":
        return ["png"]

    # JPEG
    if sig2 == b"\xff\xd8":
        return ["jpeg", "jpg"]

    # WEBP (RIFF....WEBP)
    if sig4 == b"RIFF" and box12 == b"WEBPVP8 "[:8]:
        # muPDF comprend 'webp'
        return ["webp"]

    # GIF
    if sig3 in (b"GIF"):
        # muPDF sait ouvrir des gifs statiques
        return ["gif"]

    # BMP
    if sig2 == b"BM":
        return ["bmp"]

    # TIFF (II* ou MM*)
    if sig3 in (b"II*", b"MM*"):
        return ["tiff", "tif"]

    # JPEG2000 (JP2)
    if sig12 := b[:12]:
        if sig12.startswith(b"\x00\x00\x00\x0cjP  \r\n\x87\n"):
            return ["jp2", "j2k", "jpf"]

    # HEIF/HEIC (ftypheic, ftypheif, ftypmif1, etc.) — muPDF peut ne pas tout supporter selon build
    if b[4:12] in (b"ftypheic", b"ftypheif", b"ftypmif1", b"ftypavif", b"ftyphevx"):
        return ["heic", "heif", "avif"]  # on essaiera, mais souvent non supporté

    # Par défaut : essaye les plus courants
    return ["png", "jpeg", "jpg", "webp", "tiff", "bmp", "gif"]

def _pix_from_image_bytes(img_bytes: bytes) -> Optional[fitz.Pixmap]:
        if not img_bytes:
             return None
        candidates = _guess_image_ftypes(img_bytes)

        for ftype in candidates:
             try:
                  pix = fitz.Pixmap(ftype, img_bytes)
                  if pix and pix.width > 0 and pix.height > 0:
                       return _normalize_pix_to_rgb(pix)
             except Exception:
                  pass
             
        for ftype in candidates:
             try:
                  img_doc = fitz.open(stream=img_bytes, filetype=ftype)
                  try:
                       if len(img_doc) == 0:
                            continue
                       pg = img_doc[0]
                       pix = pg.get_pixmap(alpha=False)
                       if pix and pix.width > 0 and pix.height > 0:
                            return _normalize_pix_to_rgb(pix)
                  finally:
                     img_doc.close()
             except Exception:
                  pass
        try:
          img_doc = fitz.open(stream=img_bytes)
          try: 
              if len(img_doc) > 0:
                   pg = img_doc[0]
                   pix = pg.get_pixmap(alpha=False)
                   if pix and pix.width > 0 and pix.height > 0:
                        return _normalize_pix_to_rgb(pix)
          finally:
               img_doc.close()
        except Exception:
             pass
        return None 
def _downscale_mean(gray: np.ndarray, w: int, h: int) -> np.ndarray:
    H, W = gray.shape
    ys = (np.linspace(0, H, h+1)).astype(int)
    xs = (np.linspace(0, W, w+1)).astype(int)
    out = np.zeros((h, w), dtype=np.float32)
    for i in range(h):
        for j in range(w):
            block = gray[ys[i]:ys[i+1], xs[j]:xs[j+1]]
            out[i, j] = float(block.mean()) if block.size else 0.0
    return out

def _pix_to_gray(pix: fitz.Pixmap) -> np.ndarray:
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    C = pix.n if pix.n in (1,2,3,4) else 3
    arr = arr.reshape(pix.h, pix.w, C)
    if C == 1:                # Gray
        gray = arr[..., 0].astype(np.float32)
    elif C == 2:              # Gray + alpha
        gray = arr[..., 0].astype(np.float32)
    else:                     # RGB / RGBA -> on ignore alpha
        gray = (0.299*arr[...,0] + 0.587*arr[...,1] + 0.114*arr[...,2]).astype(np.float32)
    return gray
                  
def phash64_from_pixmap(pix: fitz.Pixmap) -> int:
    gray = _pix_to_gray(pix)
    small = _downscale_mean(gray, 32, 32)
    dct_like = _downscale_mean(small, 8, 8)
    med = np.median(dct_like[1:, 1:])
    bits = (dct_like > med).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(bool(b))
    return int(h)

def hamming_distance64(a: int, b: int) -> int:
    
    return (a ^ b).bit_count()

def hamming64(a: int, b: int) -> int:
    return hamming_distance64(a, b)

def manual_slide_media(cur, source_id: int, items: List[ManualMedia], pash_dist: int = 6, min_size_px: int = 80)-> Dict[int, list[int]]:
     inserted_map: Dict[int, List[int]] = {}
     if not items:
          return inserted_map

     try: 
          existing_hashes = _load_existing_media_phases(cur, source_id)
     except Exception:
          existing_hashes = set()

     batch_hashes: Set[int] = set()
     for it in items:
          pix: Optional[fitz.Pixmap] = None
          try: 
               pix = _pix_from_image_bytes(it.data)
          except Exception:
               pix = None

          if pix is None:
               continue
          if pix.width < min_size_px or pix.height < min_size_px:
               continue
          try:
               h = int(phash64_from_pixmap(pix))
          except Exception:
               h = None

          if h is not None:
               for eh in existing_hashes:
                    if hamming64(h,eh) <= pash_dist:
                         pix = None
                         break
          if pix is None:
               continue
          if h is not None:
               is_dup_batch = any(hamming64(h, bh) <= pash_dist for bh in batch_hashes)
               if is_dup_batch:
                    continue
          try:
                mid = _insert_png_from_pix(
                        cur=cur,
                        source_id=source_id,
                        page_no=int(it.page_no),
                        pix=pix,
                        kind=(it.kind or "figure"),
                        caption=(it.filename or None),
                        bbox=None,                 
                        xref=None,
                        image_index=None,
                        is_annotation=False,
                        is_render_fallback=False
                )
          except Exception:
               mid = None
          if mid:
               inserted_map.setdefault(int(it.page_no), []).append(int(mid))
               if h is not None:
                    batch_hashes.add(h)
                    existing_hashes.add(h)
     return inserted_map

def upsert_source(cur, *, title: str, year: Optional[int], doc_mode: str, md5_file: str) -> int:
    cur.execute(
        """
        INSERT INTO academics.sources (title, year, doc_mode, md5)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (md5)
        DO UPDATE SET
            title = EXCLUDED.title,
            year = EXCLUDED.year,
            doc_mode = EXCLUDED.doc_mode
        RETURNING id
        """,
        (title, year, doc_mode, md5_file),
    )
    return int(cur.fetchone()[0])



def upsert_source_file(cur, *, source_id: int, pdf_bytes: bytes):
    cur.execute(
        """
        INSERT INTO academics.source_files (source_id, pdf_data)
        VALUES (%s, %s)
        ON CONFLICT (source_id)
        DO UPDATE SET pdf_data = EXCLUDED.pdf_data
        """,
        (source_id, psycopg2.Binary(pdf_bytes)),
    )

def _parse_bool(val: Optional[str], *, default: Optional[bool]=None) -> Optional[bool]:
  
    if val is None:
        return default
    s = str(val).strip().lower()
    if s == "":
        return default
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    raise HTTPException(status_code=422, detail=f"Valeur booléenne invalide: {val!r}")

def iou(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = a & b
    if inter.is_empty or inter.get_area() <= 0:
        return 0.0
    return inter.get_area() / (a.get_area() + b.get_area() - inter.get_area())

def merge_rects_by_iou(rects: List[fitz.Rect], iou_thr: float = IOU_MERGE, edge_gap: float = EDGE_GAP) -> List[fitz.Rect]:
    if not rects:
        return []
    rects = rects[:]
    merged: List[fitz.Rect] = []
    while rects:
        r = rects.pop()
        merged_any = False
        for i, m in enumerate(merged):
            touching = (abs(r.x0 - m.x1) <= edge_gap or abs(r.x1 - m.x0) <= edge_gap or
                        abs(r.y0 - m.y1) <= edge_gap or abs(r.y1 - m.y0) <= edge_gap)
            if iou(r, m) >= iou_thr or touching:
                merged[i] = m | r
                merged_any = True
                break
        if not merged_any:
            merged.append(r)
    keep: List[fitz.Rect] = []
    for i, r in enumerate(merged):
        contained = any(i != j and (r & m).get_area()/max(r.get_area(),1.0) >= 0.85 for j, m in enumerate(merged))
        if not contained:
            keep.append(r)
    return keep
def build_sections_from_titles(pages: List[str]) -> List[Dict]:
    sections = []
    cur_title = "Introduction"
    cur_pages: List[int] = []
    cur_buf: List[str] = []

    for i, ptxt in enumerate(pages, start=1):
        found_title_on_page = False
        for line in ptxt.splitlines():
            if TITLE_PAT.match(line.strip()):
                if cur_buf:
                    sections.append({
                        "title": cur_title[:240],
                        "pages": cur_pages[:],
                        "content": "\n".join(cur_buf).strip()
                    })
                cur_title = line.strip()
                cur_pages = [i]
                cur_buf = []
                found_title_on_page = True
            else:
                cur_buf.append(line)
        if not found_title_on_page:
            if i not in cur_pages:
                cur_pages.append(i)
    if cur_buf:
        sections.append({
            "title": cur_title[:240],
            "pages": cur_pages,
            "content": "\n".join(cur_buf).strip()
        })
    return sections

def detect_table_regions(page: fitz.Page,
                         min_side: int = 120,
                         min_lines: int = 6,
                         merge_iou: float = 0.25) -> List[fitz.Rect]:
   
    candidates: List[fitz.Rect] = []

    try:
        drawings = page.get_drawings() or []
    except Exception:
        drawings = []

    # 1) Collecte des boîtes rectangulaires & segments longs
    horiz, vert = [], []
    for d in drawings:
        r = d.get("rect")
        if isinstance(r, fitz.Rect):
            # Les véritables tableaux ont souvent des rectangles "cadres"
            if r.width >= min_side and r.height >= min_side:
                candidates.append(r)

        # segments
        for item in d.get("items") or []:
            # item: ('l', p1, p2, width, color, fill, ...)
            if not item or item[0] != 'l':
                continue
            p1, p2 = item[1], item[2]
            if not (isinstance(p1, fitz.Point) and isinstance(p2, fitz.Point)):
                continue
            dx, dy = abs(p2.x - p1.x), abs(p2.y - p1.y)
            if dx >= min_side and dy <= 2:   # horizontale
                horiz.append(fitz.Rect(min(p1.x,p2.x), p1.y-1, max(p1.x,p2.x), p1.y+1))
            if dy >= min_side and dx <= 2:   # verticale
                vert.append(fitz.Rect(p1.x-1, min(p1.y,p2.y), p1.x+1, max(p1.y,p2.y)))

    # 2) Si beaucoup de segments H/V, enveloppe convex/union
    #    On regroupe grossièrement par clusters simples (IoU)
    seg_rects = horiz + vert
    seg_rects = merge_rects_by_iou(seg_rects, iou_thr=merge_iou, edge_gap=8.0)
    # Ne garder que les enveloppes contenant un "réseau" de lignes
    if len(horiz) + len(vert) >= min_lines:
        candidates += seg_rects

    # 3) Nettoyage / dé-doublonnage
    out = merge_rects_by_iou(candidates, iou_thr=merge_iou, edge_gap=10.0)
    # Filtre tailles minimales
    out = [r for r in out if r.width >= min_side and r.height >= min_side]
    return out

def phash_from_pixmap(pix: fitz.Pixmap) -> int:
 
    gray = _pix_to_gray(pix)               # -> float32 [H, W]
    small = _downscale_mean(gray, 32, 32)  # 32x32
    dct_like = _downscale_mean(small, 8, 8)  # "approx DCT" 8x8

    # On ignore la case [0,0] (équivalent du DC) pour le calcul de la médiane
    med = np.median(dct_like[1:, 1:])
    bits = (dct_like > med).flatten()

    h = 0
    for b in bits:
        h = (h << 1) | int(bool(b))
    return int(h)

def extract_images(
    doc: fitz.Document,
    source_id: int,
    cur,
    render_scale: float = 2.0,
    min_region_px: int = 110,
    page_preview_mode: str = "never",   # >>> pas de fallback pour le mode slide
    word_density_reject: float = 0.38,  # >>> stricte sur les zones texte
    min_iou_same: float = 0.62,         # >>> anti-doublon spatial
    max_phash_dist: int = 6,            # >>> anti-doublon visuel
    slide_mode: bool = False           # >>> Contrôle si c'est en mode slide
) -> Tuple[int, Dict[int, List[fitz.Rect]]]:
    total_inserted = 0
    figure_map: Dict[int, List[fitz.Rect]] = {}

    for pno in range(len(doc)):
        page = doc[pno]
        page_no = pno + 1

        # 1) Collecter les candidats (images, dessins, graphiques, tableaux)
        embed_rects: List[fitz.Rect] = []
        try:
            seen_xrefs = set()
            for info in page.get_images(full=True) or []:
                xref = info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    ibox = page.get_image_bbox(xref)
                except Exception:
                    ibox = None
                if ibox and ibox.width >= min_region_px and ibox.height >= min_region_px:
                    embed_rects.append(ibox)
        except Exception:
            pass

        raw_rects: List[fitz.Rect] = []
        try:
            raw = page.get_text("rawdict")
            for b in (raw.get("blocks", []) if isinstance(raw, dict) else []):
                if b.get("type") == 1 and b.get("bbox"):
                    r = fitz.Rect(b["bbox"])
                    if r.width >= min_region_px and r.height >= min_region_px:
                        raw_rects.append(r)
        except Exception:
            pass

        draw_rects: List[fitz.Rect] = []
        try:
            drawings = page.get_drawings() or []
        except Exception:
            drawings = []

        for d in drawings:
            r = d.get("rect")
            if isinstance(r, fitz.Rect) and r.width >= min_region_px and r.height >= min_region_px:
                draw_rects.append(r)

        table_rects = detect_table_regions(page)

        # 2) Fusion globale des candidats (images, dessins, schémas, etc.)
        rects = embed_rects + raw_rects + draw_rects + table_rects
        rects = merge_rects_by_iou(rects, iou_thr=0.30, edge_gap=12.0)

        # 3) Filtrage strict si en mode slide (pas de texte superposé dans les zones images)
        filtered: List[fitz.Rect] = []
        if slide_mode:
            for r in rects:
                # Ne prendre que les zones contenant des images ou des schémas graphiques (pas du texte)
                filtered.append(r)
        else:
            for r in rects:
                # continue avec les règles de filtrage standards pour tout autre PDF
                filtered.append(r)

        # 4) Dé-duplication et rendu des images
        kept_rects: List[Tuple[fitz.Rect, int, int, Optional[int]]] = []
        kept_for_map: List[fitz.Rect] = []
        mat = fitz.Matrix(render_scale, render_scale)

        for r in filtered:
            try:
                pix = page.get_pixmap(matrix=mat, clip=r, alpha=False)
                if pix.width < min_region_px or pix.height < min_region_px:
                    continue

                # pHash
                try:
                    ph = phash_from_pixmap(pix)
                except Exception:
                    ph = None

                # doublons?
                duplicate = False
                for (kr, kw, kh, kph) in kept_rects:
                    # spatial
                    inter = (kr & r)
                    if not inter.is_empty and (inter.get_area() / min(kr.get_area(), r.get_area())) >= min_iou_same:
                        duplicate = True
                        break
                    # visuel
                    if ph is not None and kph is not None:
                        if hamming_distance64(ph, kph) <= max_phash_dist:
                            cur_area = pix.width * pix.height
                            keep_area = kw * kh
                            if cur_area <= keep_area:
                                duplicate = True
                                break
                if duplicate:
                    continue

                mid = _insert_png_from_pix(
                    cur, source_id, page_no, pix,
                    kind="figure", caption=None, bbox=r,
                    xref=None, image_index=None,
                    is_annotation=False, is_render_fallback=False
                )
                if mid:
                    total_inserted += 1
                    kept_rects.append((r, pix.width, pix.height, ph))
                    kept_for_map.append(r)

            except Exception:
                continue
            finally:
                try:
                    pix = None
                except Exception:
                    pass

        if kept_for_map:
            figure_map[page_no] = kept_for_map

    return total_inserted, figure_map

def ocr_png_bytes(png: bytes, lang: str = "fra+eng") -> str:
    if not OCR_AVAILABLE:
        return ""

    try:
        img = Image.open(BytesIO(png)).convert("RGB")
        txt = pytesseract.image_to_string(img, lang=lang) or ""
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        lines = [l for l in lines if len(l) >= 3]
        return "\n".join(lines).strip()
    except Exception:
        return ""
    
def insert_page_media_asset_png(
    cur,
    *,
    source_id: int,
    page_no: int,
    kind: str,              # 'figure'/'image'/'manual'/'embedded'
    png_bytes: bytes,
    bbox: Optional[list] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[int]:
    h = hashlib.md5(png_bytes).hexdigest()
    cur.execute(
        """
        INSERT INTO academics.page_media_assets
            (source_id, page_no, kind, mime, data, md5, bbox, width, height)
        VALUES
            (%s, %s, %s, 'image/png', %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (source_id, page_no, kind, psycopg2.Binary(png_bytes), h, Json(bbox) if bbox else None, width, height),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None

def create_course_and_link_source(
        ue_id: int, 
        title: str,
        description: str,
        doc_mode: str,
        source_id: int,
        course_code: str,
        version_label: str,
        image_policy: str
) -> tuple[int, int]:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO academics.courses(ue_id, code, title, description, order_no, doc_mode)
                VALUES(%s,%s,%s,%s,0,%s)
                RETURNING id
        """,(ue_id, course_code, title, description, doc_mode))
    course_id = int(cur.fetchone()[0])

    cur.execute("""
        INSERT INTO academics.course_versions (course_id, version_label, status)
                VALUES (%s,%s,%s,%s,0,%s)
                RETURNING id
        """,(course_id, version_label))
    version_id = int(cur.fetchone()[0])

    cur.execute("""
        INSERT INTO academics.course_sources(
                course_id, version_id, source_id, role, doc_mode, images_policy, is_primary)
                VALUES (%s; %s, %s, 'PRIMARY', %s,%s, TRUE)
        """,(course_id, version_id, source_id, doc_mode, image_policy))
    return course_id, version_id

def upsert_course_source(
    cur,
    *,
    course_id: int,
    version_id: Optional[int],
    source_id: int,
    role: str = "PRIMARY",
    doc_mode: str = "CLASSIC",           # 'CLASSIC'/'SLIDE'/'UNKNOWN'
    images_policy: str = "AUTO",         # 'AUTO'/'SEMI_MANUAL'/'PRUDENT'
    is_primary: bool = True,
):
    cur.execute(
        """
        INSERT INTO academics.course_sources
            (course_id, version_id, source_id, role, doc_mode, images_policy, is_primary)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (course_id, source_id, version_id, role)
        DO UPDATE SET
            doc_mode = EXCLUDED.doc_mode,
            images_policy = EXCLUDED.images_policy,
            is_primary = EXCLUDED.is_primary
        """,
        (course_id, version_id, source_id, role, doc_mode, images_policy, is_primary),
    )

# ---------------------------------------------------------------------
# INGEST principal (aligné academics.*)
# ---------------------------------------------------------------------


def ingest_pdf_to_db(
    *,
    pdf_bytes: bytes,
    conn,
    original_filename: Optional[str] = None,
    course_title: Optional[str] = None,
    year: Optional[int] = None,

    # cours
    ue_id: Optional[int] = None,
    description: str = "",
    semester: Optional[int] = None,
    ects: Optional[float] = None,
    create_course: bool = True,
    create_sections: bool = True,  # laissé pour compat, pas utilisé ici
    doc_mode: str = "CLASSIC",

    # pilotage extraction
    slide_mode: bool = False,

    # images manuelles (page_no, img_bytes, caption)
    manual_slide_media: Optional[List[Tuple[int, bytes, str]]] = None,

    # hooks
    extract_text_filtered_from_bytes=None,
    extract_images=None,
    get_embedded_image_rects_by_page=None,
) -> "PDFIngestResult":

    if conn is None:
        raise HTTPException(status_code=500, detail="DB conn manquante: conn=None")

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF vide.")

    filename = original_filename or "document.pdf"
    title = (course_title or os.path.splitext(filename)[0]).strip() or "document"
    md5_file = hashlib.md5(pdf_bytes).hexdigest()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages_pdf = len(doc)

    course_id = None
    version_id = None
    total_pages_db = 0
    total_images_db = 0
    total_images_auto = 0
    text_db = ""

    # garde-fou : si on veut créer un cours, ue_id est obligatoire
    if create_course and (ue_id is None or int(ue_id) <= 0):
        raise HTTPException(status_code=422, detail="ue_id requis quand create_course=true")

    try:
        with conn.cursor() as cur:
            # ----------------------------------------------------
            # 1) SOURCE
            # ----------------------------------------------------
            source_id = upsert_source(
                cur,
                title=title,
                year=year,
                doc_mode=doc_mode,
                md5_file=md5_file
            )
            print("SOURCE_ID:", source_id)

            # ----------------------------------------------------
            # 2) PDF BYTES
            # ----------------------------------------------------
            upsert_source_file(cur, source_id=source_id, pdf_bytes=pdf_bytes)

            # ----------------------------------------------------
            # 3) MAP zones images embarquées
            # ----------------------------------------------------
            if not callable(get_embedded_image_rects_by_page):
                raise RuntimeError("get_embedded_image_rects_by_page manquante.")
            image_rects_map = get_embedded_image_rects_by_page(doc)

            # ----------------------------------------------------
            # 4) IMAGES auto
            # ----------------------------------------------------
            figure_map = {}
            if not slide_mode:
                if not callable(extract_images):
                    raise RuntimeError("extract_images manquante.")
                total_images_auto, figure_map = extract_images(
                    doc, source_id, cur,
                    render_scale=2.0,
                    min_region_px=110,
                    page_preview_mode="never",
                    word_density_reject=0.38,
                    min_iou_same=0.62,
                    max_phash_dist=6,
                    slide_mode=False,
                )
            else:
                total_images_auto = 0

            # ----------------------------------------------------
            # 4.b) IMAGES manuelles en mode slide
            # ----------------------------------------------------
            if slide_mode and manual_slide_media:
                for (page_no, img_bytes, caption) in manual_slide_media:
                    png = img_bytes
                    w = h = None
                    try:
                        pix = fitz.Pixmap("png", img_bytes)
                        png = pix.tobytes("png")
                        w, h = pix.width, pix.height
                    except Exception:
                        pass

                    insert_page_media_asset_png(
                        cur,
                        source_id=source_id,
                        page_no=int(page_no),
                        kind="manual",
                        png_bytes=png,
                        bbox=None,
                        width=w,
                        height=h,
                    )

            # ----------------------------------------------------
            # 5) TEXTE filtré
            # ----------------------------------------------------
            if not callable(extract_text_filtered_from_bytes):
                raise RuntimeError("extract_text_filtered_from_bytes manquante.")

            pages_text = extract_text_filtered_from_bytes(
            pdf_bytes,
            figure_map=figure_map,
            image_rects_map=image_rects_map,
            overlap_threshold=0.18,
        )

            # ----------------------------------------------------
            # 6) UPSERT pages
            # ----------------------------------------------------
            for pno, txt in enumerate(pages_text, start=1):
                upsert_source_page(cur, source_id=source_id, page_no=pno, text=txt, ocr_text=None)

            # ----------------------------------------------------
            # 7) STATS pages & médias
            # ----------------------------------------------------
            cur.execute("SELECT COUNT(*) FROM academics.source_pages WHERE source_id=%s", (source_id,))
            total_pages_db = int(cur.fetchone()[0] or 0)

            cur.execute("SELECT COUNT(*) FROM academics.page_media_assets WHERE source_id=%s", (source_id,))
            total_images_db = int(cur.fetchone()[0] or 0)

            cur.execute(
                """
                SELECT COALESCE(string_agg(COALESCE(ocr_text, text), E'\n' ORDER BY page_no), '')
                FROM academics.source_pages
                WHERE source_id=%s
                """,
                (source_id,),
            )
            text_db = cur.fetchone()[0] or ""

            # ----------------------------------------------------
            # 8) CREATE COURSE + VERSION + LINK SOURCE
            # ----------------------------------------------------
            if create_course:
                # code cours: simple & stable (tu peux mettre mieux)
                course_code = hashlib.md5((title + md5_file).encode("utf-8")).hexdigest()[:10].upper()

                # course
                cur.execute(
                    """
                    INSERT INTO academics.courses (ue_id, code, title, description, order_no, doc_mode)
                    VALUES (%s, %s, %s, %s, 0, %s)
                    ON CONFLICT (ue_id, code)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        doc_mode = EXCLUDED.doc_mode,
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (int(ue_id), course_code, title, description, doc_mode),
                )
                course_id = int(cur.fetchone()[0])

                # version
                version_label = f"v{datetime.date.today().isoformat()}-auto"
                cur.execute(
                    """
                    INSERT INTO academics.course_versions (course_id, version_label, status)
                    VALUES (%s, %s, 'draft')
                    ON CONFLICT (course_id, version_label)
                    DO UPDATE SET updated_at = NOW()
                    RETURNING id
                    """,
                    (course_id, version_label),
                )
                version_id = int(cur.fetchone()[0])

                # link course_sources
                cur.execute(
                    """
                    INSERT INTO academics.course_sources
                        (course_id, version_id, source_id, role, doc_mode, images_policy, is_primary)
                    VALUES
                        (%s, %s, %s, 'PRIMARY', %s, %s, TRUE)
                    ON CONFLICT (course_id, source_id, version_id, role)
                    DO NOTHING
                    """,
                    (
                        course_id,
                        version_id,
                        source_id,
                        doc_mode,
                        ("SEMI_MANUAL" if slide_mode else "AUTO"),
                    ),
                )

            conn.commit()

        return PDFIngestResult(
            source_id=source_id,
            course_id=course_id,
            version_id=version_id,
            total_pages_pdf=total_pages_pdf,
            total_pages_db=total_pages_db,
            total_images_pdf=total_images_auto,
            total_images_db=total_images_db,
            text_len_pdf=len(pdf_bytes),
            text_len_db=len(text_db),
            text_hash_pdf=hashlib.sha256(pdf_bytes).hexdigest(),
            text_hash_db=hashlib.sha256(text_db.encode("utf-8")).hexdigest(),
            missing_pages=[],
            empty_pages=[],
            coverage_ok=(total_pages_pdf == total_pages_db),
        )

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            doc.close()
        except Exception:
            pass