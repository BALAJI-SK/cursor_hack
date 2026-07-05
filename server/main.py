import os
import uuid
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image

from database import init_db, get_db_connection
from archive_manager import ArchiveManager
from model_runner import ModelRunner
from pipeline.decoder import YoloPanelDecoder
from pipeline.pipeline import PanelPipeline

init_db()

app = FastAPI(title="Chika API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

archive_manager = ArchiveManager()

# Find the model across multiple potential locations
model_candidates = [
    "app/src/main/assets/manga_panel_detector_int8.tflite",
    "../app/src/main/assets/manga_panel_detector_int8.tflite",
    "/app/manga_panel_detector_int8.tflite",
    "manga_panel_detector_int8.tflite"
]
model_path = None
for candidate in model_candidates:
    if os.path.exists(candidate):
        model_path = candidate
        break

print(f"[DEBUG] Current working directory: {os.getcwd()}")
print(f"[DEBUG] Files in current directory: {os.listdir('.')}")
print(f"[DEBUG] Selected model path: {model_path}")

if model_path is None:
    # Set default but raise warning
    model_path = "app/src/main/assets/manga_panel_detector_int8.tflite"
    print(f"Warning: model not found in candidates, defaulting to {model_path}")

model_runner = ModelRunner(model_path)
decoder = YoloPanelDecoder()

@app.get("/api/comics")
def get_comics():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, total_pages, progress_page, progress_panel FROM comics")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "title": r[1],
            "totalPages": r[2],
            "progressPage": r[3],
            "progressPanel": r[4]
        } for r in rows
    ]

@app.post("/api/comics/import")
async def import_comic(file: UploadFile = File(...)):
    comic_id = str(uuid.uuid4())
    file_path = f"uploads/{comic_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    pages = archive_manager.list_pages(file_path)
    if not pages:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Invalid archive or no images found")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comics (id, title, file_path, total_pages) VALUES (?, ?, ?, ?)",
        (comic_id, file.filename, file_path, len(pages))
    )
    conn.commit()
    conn.close()
    return {"id": comic_id}

@app.delete("/api/comics/{comic_id}")
def delete_comic(comic_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM comics WHERE id = ?", (comic_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Comic not found")
    
    file_path = row[0]
    if os.path.exists(file_path):
        os.remove(file_path)
        
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/comics/{comic_id}/cover")
def get_cover(comic_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM comics WHERE id = ?", (comic_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Comic not found")
    
    cover_bytes = archive_manager.extract_cover_thumbnail(row[0])
    return Response(content=cover_bytes, media_type="image/jpeg")

@app.get("/api/comics/{comic_id}/pages/{page_num}")
def get_page(comic_id: str, page_num: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM comics WHERE id = ?", (comic_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Comic not found")
    
    pages = archive_manager.list_pages(row[0])
    if page_num < 0 or page_num >= len(pages):
        raise HTTPException(status_code=404, detail="Page index out of bounds")
        
    page_bytes = archive_manager.extract_page(row[0], pages[page_num])
    img = Image.open(io.BytesIO(page_bytes))
    if img.width > 2048 or img.height > 2048:
        img.thumbnail((2048, 2048))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return Response(content=out.getvalue(), media_type="image/jpeg")

@app.get("/api/comics/{comic_id}/pages/{page_num}/panels")
def get_panels(comic_id: str, page_num: int, rtl: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM comics WHERE id = ?", (comic_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Comic not found")
    
    pages = archive_manager.list_pages(row[0])
    if page_num < 0 or page_num >= len(pages):
        raise HTTPException(status_code=404, detail="Page index out of bounds")
        
    page_bytes = archive_manager.extract_page(row[0], pages[page_num])
    img = Image.open(io.BytesIO(page_bytes))
    
    # Run inference and get zoom regions
    raw_out, lb = model_runner.run_inference(img)
    decoded = decoder.decode(raw_out[0], lb)
    regions = PanelPipeline.zoom_regions(decoded["panels"], decoded["bubbles"], img.width, img.height, rtl)
    return [r.to_dict() for r in regions]

@app.post("/api/comics/{comic_id}/progress")
def update_progress(comic_id: str, progress: dict):
    page = progress.get("page", 0)
    panel = progress.get("panel", 0)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE comics SET progress_page = ?, progress_panel = ? WHERE id = ?",
        (page, panel, comic_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}
