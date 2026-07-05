import os
import uuid
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from PIL import Image

from database import init_db, get_db_connection
from archive_manager import ArchiveManager
from model_runner import ModelRunner
from pipeline.decoder import YoloPanelDecoder
from pipeline.pipeline import PanelPipeline
from pipeline.nvidia_client import NvidiaVlmClient
from pipeline.audio_generator import AudioGenerator

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

nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")
eleven_api_key = os.getenv("ELEVEN_API_KEY", "")
nvidia_client = NvidiaVlmClient(api_key=nvidia_api_key)
audio_generator = AudioGenerator(api_key=eleven_api_key)

def process_comic_background(comic_id: str, file_path: str):
    conn = None
    try:
        pages = archive_manager.list_pages(file_path)
        conn = get_db_connection()
        for idx, page_name in enumerate(pages):
            page_bytes = archive_manager.extract_page(file_path, page_name)
            img = Image.open(io.BytesIO(page_bytes))
            # Call process_page from pipeline
            from pipeline.pipeline import process_page
            process_page(
                comic_id=comic_id,
                page_number=idx,
                img=img,
                model_runner=model_runner,
                decoder=decoder,
                nvidia_client=nvidia_client,
                audio_generator=audio_generator,
                db_conn=conn,
                rtl=False
            )
    except Exception as e:
        print(f"[ERROR] Background processing failed for comic {comic_id}: {e}")
    finally:
        if conn is not None:
            conn.close()

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
async def import_comic(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
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
    
    if background_tasks:
        background_tasks.add_task(process_comic_background, comic_id, file_path)
        
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
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM comics WHERE id = ?", (comic_id,))
        row = cursor.fetchone()
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
        regions_ltr = PanelPipeline.zoom_regions(decoded["panels"], decoded["bubbles"], img.width, img.height, False)
        
        # Get audio URLs
        cursor.execute("""
            SELECT panel_index, audio_path, sfx_path FROM panel_audio
            WHERE comic_id = ? AND page_number = ?
        """, (comic_id, page_num))
        audio_rows = cursor.fetchall()
    finally:
        conn.close()
    
    audio_map = {}
    for r in audio_rows:
        panel_idx = r[0]
        audio_path = r[1]
        sfx_path = r[2]
        
        audio_url = None
        sfx_url = None
        
        if audio_path and os.path.exists(audio_path):
            audio_url = f"/api/audio/{comic_id}/{os.path.basename(audio_path)}"
        if sfx_path and os.path.exists(sfx_path):
            sfx_url = f"/api/audio/{comic_id}/{os.path.basename(sfx_path)}"
            
        audio_map[panel_idx] = {
            "audioUrl": audio_url,
            "sfxUrl": sfx_url
        }
        
    res_list = []
    for idx, r in enumerate(regions):
        r_dict = r.to_dict()
        # Find index of coordinate match in regions_ltr within 1e-4 tolerance
        matched_idx = None
        for ltr_idx, r_ltr in enumerate(regions_ltr):
            if (abs(r.left - r_ltr.left) < 1e-4 and
                abs(r.top - r_ltr.top) < 1e-4 and
                abs(r.right - r_ltr.right) < 1e-4 and
                abs(r.bottom - r_ltr.bottom) < 1e-4):
                matched_idx = ltr_idx
                break
        if matched_idx is None:
            matched_idx = idx
            
        audio_info = audio_map.get(matched_idx, {"audioUrl": None, "sfxUrl": None})
        r_dict["audioUrl"] = audio_info["audioUrl"]
        r_dict["sfxUrl"] = audio_info["sfxUrl"]
        res_list.append(r_dict)
        
    return res_list

@app.get("/api/audio/{comic_id}/{filename}")
def stream_audio(comic_id: str, filename: str):
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    if not safe_filename.startswith(f"{comic_id}_"):
        raise HTTPException(status_code=403, detail="Access denied to this comic's audio")
    audio_dir = "uploads/audio"
    file_path = os.path.join(audio_dir, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")

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
