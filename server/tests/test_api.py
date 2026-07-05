import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from database import init_db

client = TestClient(app)

def test_api_endpoints():
    # Make sure DB is initialized
    init_db()

    # Get comics (should be empty initially)
    response = client.get("/api/comics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Try fetching a non-existent cover or progress
    response = client.get("/api/comics/nonexistent/cover")
    assert response.status_code == 404

    response = client.post("/api/comics/nonexistent/progress", json={"page": 5, "panel": 2})
    assert response.status_code == 200


def test_delete_comic_deletes_audio_files():
    from database import get_db_connection
    init_db()

    comic_id = "test-delete-comic-id"
    comic_file = "uploads/test-delete-comic-archive.zip"
    audio_path = "uploads/audio/test-delete-comic_p0_panel0_narration.mp3"
    sfx_path = "uploads/audio/test-delete-comic_p0_panel0_sfx.mp3"

    # Create dummy files on disk
    os.makedirs("uploads/audio", exist_ok=True)
    with open(comic_file, "w") as f:
        f.write("dummy zip content")
    with open(audio_path, "w") as f:
        f.write("dummy audio content")
    with open(sfx_path, "w") as f:
        f.write("dummy sfx content")

    # Insert mock DB records
    conn = get_db_connection()
    cursor = conn.cursor()
    # Clean up first
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
    
    cursor.execute(
        "INSERT INTO comics (id, title, file_path, total_pages) VALUES (?, ?, ?, ?)",
        (comic_id, "Test Delete Comic", comic_file, 1)
    )
    cursor.execute(
        "INSERT INTO panel_audio (id, comic_id, page_number, panel_index, audio_path, sfx_path) VALUES (?, ?, ?, ?, ?, ?)",
        ("test-audio-id", comic_id, 0, 0, audio_path, sfx_path)
    )
    conn.commit()
    conn.close()

    # Assert files exist before delete
    assert os.path.exists(comic_file)
    assert os.path.exists(audio_path)
    assert os.path.exists(sfx_path)

    # Perform deletion via API
    response = client.delete(f"/api/comics/{comic_id}")
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Assert files are deleted
    assert not os.path.exists(comic_file)
    assert not os.path.exists(audio_path)
    assert not os.path.exists(sfx_path)

    # Assert DB records are deleted
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comics WHERE id = ?", (comic_id,))
    assert cursor.fetchone() is None
    cursor.execute("SELECT * FROM panel_audio WHERE comic_id = ?", (comic_id,))
    assert cursor.fetchone() is None
    conn.close()


def test_process_comic_background_liveness_check(tmp_path):
    from PIL import Image
    import io
    import zipfile
    from unittest.mock import patch
    from main import process_comic_background
    from database import init_db

    init_db()

    # Create mock CBZ/zip
    cbz_path = tmp_path / "comic_liveness.cbz"
    with zipfile.ZipFile(cbz_path, 'w') as z:
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        z.writestr("page1.jpg", img_bytes.getvalue())

    # We do NOT insert this comic into the database.
    comic_id = "nonexistent-liveness-id"

    # Mock pipeline's process_page to verify it's never called
    with patch("pipeline.pipeline.process_page") as mock_process_page:
        process_comic_background(comic_id, str(cbz_path))
        mock_process_page.assert_not_called()


