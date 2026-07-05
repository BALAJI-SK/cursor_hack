import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os
import io
import sqlite3
import zipfile
from PIL import Image

from server.main import app
from server.database import get_db_connection, init_db
from server.pipeline.panel import Panel

client = TestClient(app)

def test_audio_generation_and_streaming():
    init_db()
    
    # Insert a dummy comic to the DB
    comic_id = "test-comic-123"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
    cursor.execute(
        "INSERT INTO comics (id, title, file_path, total_pages) VALUES (?, ?, ?, ?)",
        (comic_id, "Test Comic", "test_file.zip", 1)
    )
    conn.commit()
    conn.close()
    
    # Prepare dummy image
    img = Image.new("RGB", (100, 100))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()
    
    # Setup mocks for processing
    mock_nvidia = MagicMock()
    mock_nvidia.analyze_panel.return_value = {
        "dialogue": "Hello narrative!",
        "sfx": "Boom"
    }
    
    mock_audio_gen = MagicMock()
    # Let's mock generate_tts and generate_sfx to write fake files
    audio_filename = f"{comic_id}_p0_panel0_narration.mp3"
    sfx_filename = f"{comic_id}_p0_panel0_sfx.mp3"
    audio_path = os.path.join("uploads", "audio", audio_filename)
    sfx_path = os.path.join("uploads", "audio", sfx_filename)
    
    # Make sure directories exist and delete existing files
    os.makedirs("uploads/audio", exist_ok=True)
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(sfx_path):
        os.remove(sfx_path)
        
    def side_effect_tts(text, path):
        with open(path, "wb") as f:
            f.write(b"tts_audio_bytes")
    def side_effect_sfx(desc, path):
        with open(path, "wb") as f:
            f.write(b"sfx_audio_bytes")
            
    mock_audio_gen.generate_tts.side_effect = side_effect_tts
    mock_audio_gen.generate_sfx.side_effect = side_effect_sfx
    
    mock_model_runner = MagicMock()
    mock_model_runner.run_inference.return_value = ([None], {})
    
    mock_decoder = MagicMock()
    mock_decoder.decode.return_value = {"panels": [], "bubbles": []}
    
    # Call process_page directly to check DB integration
    from server.pipeline.pipeline import process_page
    conn = get_db_connection()
    process_page(
        comic_id=comic_id,
        page_number=0,
        img=img,
        model_runner=mock_model_runner,
        decoder=mock_decoder,
        nvidia_client=mock_nvidia,
        audio_generator=mock_audio_gen,
        db_conn=conn,
        rtl=False
    )
    conn.close()
    
    # Verify file was written
    assert os.path.exists(audio_path)
    assert os.path.exists(sfx_path)
    
    # Let's mock main model_runner, decoder, and archive_manager to test panels endpoint
    with patch("server.main.model_runner", mock_model_runner), \
         patch("server.main.decoder", mock_decoder), \
         patch("server.main.archive_manager") as mock_archive_manager:
        
        mock_archive_manager.list_pages.return_value = ["page1.jpg"]
        mock_archive_manager.extract_page.return_value = img_bytes
        
        # Now query the panels endpoint
        # Since regions will be returned from PanelPipeline.zoom_regions, let's mock zoom_regions
        with patch("server.main.PanelPipeline.zoom_regions") as mock_zoom:
            mock_zoom.return_value = [Panel(0.0, 0.0, 0.5, 0.5)]
            
            response = client.get(f"/api/comics/{comic_id}/pages/0/panels")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["audioUrl"] == f"/api/audio/{comic_id}/{audio_filename}"
            assert data[0]["sfxUrl"] == f"/api/audio/{comic_id}/{sfx_filename}"
            
    # Test streaming endpoint
    response = client.get(f"/api/audio/{comic_id}/{audio_filename}")
    assert response.status_code == 200
    assert response.content == b"tts_audio_bytes"
    
    response = client.get(f"/api/audio/{comic_id}/{sfx_filename}")
    assert response.status_code == 200
    assert response.content == b"sfx_audio_bytes"
    
    # Test streaming endpoint for nonexistent file (invalid prefix -> 403)
    response = client.get(f"/api/audio/{comic_id}/nonexistent.mp3")
    assert response.status_code == 403
    
    # Test streaming endpoint for nonexistent file (valid prefix, missing file -> 404)
    response = client.get(f"/api/audio/{comic_id}/{comic_id}_nonexistent.mp3")
    assert response.status_code == 404
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(sfx_path):
        os.remove(sfx_path)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
    conn.commit()
    conn.close()

def test_import_comic_with_audio_pipeline(tmp_path):
    init_db()
    
    # Create mock CBZ
    cbz_path = tmp_path / "comic.cbz"
    with zipfile.ZipFile(cbz_path, 'w') as z:
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        z.writestr("page1.jpg", img_bytes.getvalue())
        
    # Mock VLM and Audio Generator API/client calls
    mock_nvidia = MagicMock()
    mock_nvidia.analyze_panel.return_value = {
        "dialogue": "Narrated text",
        "sfx": "slash"
    }
    
    mock_audio_gen = MagicMock()
    # We will write dummy files for the generated audio in the uploads folder
    def side_effect_tts(text, path):
        with open(path, "wb") as f:
            f.write(b"tts_bytes")
    def side_effect_sfx(desc, path):
        with open(path, "wb") as f:
            f.write(b"sfx_bytes")
            
    mock_audio_gen.generate_tts.side_effect = side_effect_tts
    mock_audio_gen.generate_sfx.side_effect = side_effect_sfx
    
    mock_model_runner = MagicMock()
    mock_model_runner.run_inference.return_value = ([None], {})
    
    mock_decoder = MagicMock()
    mock_decoder.decode.return_value = {"panels": [], "bubbles": []}
    
    # Patch clients in main
    with patch("server.main.nvidia_client", mock_nvidia), \
         patch("server.main.audio_generator", mock_audio_gen), \
         patch("server.main.model_runner", mock_model_runner), \
         patch("server.main.decoder", mock_decoder), \
         patch("server.main.PanelPipeline.zoom_regions") as mock_zoom:
         
        mock_zoom.return_value = [Panel(0.0, 0.0, 0.5, 0.5)]
        
        # Post request to import comic
        with open(cbz_path, "rb") as f:
            response = client.post(
                "/api/comics/import",
                files={"file": ("comic.cbz", f, "application/zip")}
            )
            
        assert response.status_code == 200
        comic_id = response.json()["id"]
        assert comic_id is not None
        
        # Verify the database contains panel audio entry
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dialogue_text, sfx_description, audio_path, sfx_path FROM panel_audio WHERE comic_id = ?", (comic_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row[0] == "Narrated text"
        assert row[1] == "slash"
        assert row[2] is not None
        assert row[3] is not None
        
        # Verify get_panels returns correct audio URLs
        response = client.get(f"/api/comics/{comic_id}/pages/0/panels")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "audioUrl" in data[0]
        assert "sfxUrl" in data[0]
        assert data[0]["audioUrl"] == f"/api/audio/{comic_id}/{os.path.basename(row[2])}"
        assert data[0]["sfxUrl"] == f"/api/audio/{comic_id}/{os.path.basename(row[3])}"
        
        # Verify audio streaming endpoint works
        audio_url = data[0]["audioUrl"]
        response = client.get(audio_url)
        assert response.status_code == 200
        assert response.content == b"tts_bytes"
        
        sfx_url = data[0]["sfxUrl"]
        response = client.get(sfx_url)
        assert response.status_code == 200
        assert response.content == b"sfx_bytes"
        
        # Clean up database for this comic
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
        cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
        conn.commit()
        conn.close()
        
        # Clean up files
        if os.path.exists(row[2]):
            os.remove(row[2])
        if os.path.exists(row[3]):
            os.remove(row[3])


def test_rtl_audio_coordinate_matching_and_resilience():
    init_db()
    comic_id = "test-comic-rtl-resilience"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
    cursor.execute(
        "INSERT INTO comics (id, title, file_path, total_pages) VALUES (?, ?, ?, ?)",
        (comic_id, "RTL Test Comic", "test_file.zip", 1)
    )
    # Insert an audio row mapped to panel_index = 0, which corresponds to the first panel in LTR order.
    audio_path = os.path.join("uploads", "audio", f"{comic_id}_p0_panel0_narration.mp3")
    os.makedirs("uploads/audio", exist_ok=True)
    with open(audio_path, "wb") as f:
        f.write(b"panel0_ltr_audio")
        
    cursor.execute("""
        INSERT INTO panel_audio (id, comic_id, page_number, panel_index, dialogue_text, sfx_description, audio_path, sfx_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (f"{comic_id}_0_0", comic_id, 0, 0, "Dialogue Panel 0 LTR", "SFX Panel 0 LTR", audio_path, None))
    conn.commit()
    conn.close()

    img = Image.new("RGB", (100, 100))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    mock_model_runner = MagicMock()
    mock_model_runner.run_inference.return_value = ([None], {})
    mock_decoder = MagicMock()
    mock_decoder.decode.return_value = {"panels": [], "bubbles": []}

    panel_A = Panel(0.0, 0.0, 0.5, 1.0)
    panel_B = Panel(0.5, 0.0, 1.0, 1.0)

    def side_effect_zoom_regions(panels, bubbles, w, h, rightToLeft):
        if rightToLeft:
            return [panel_B, panel_A]
        else:
            return [panel_A, panel_B]

    with patch("server.main.model_runner", mock_model_runner), \
         patch("server.main.decoder", mock_decoder), \
         patch("server.main.archive_manager") as mock_archive_manager, \
         patch("server.main.PanelPipeline.zoom_regions", side_effect=side_effect_zoom_regions):

        mock_archive_manager.list_pages.return_value = ["page1.jpg"]
        mock_archive_manager.extract_page.return_value = img_bytes

        # Query panels with rtl=True
        response = client.get(f"/api/comics/{comic_id}/pages/0/panels?rtl=true")
        assert response.status_code == 200
        data = response.json()
        
        # There should be 2 panels:
        # index 0 should be Panel B (left=0.5), which is at index 1 in LTR order.
        # index 1 should be Panel A (left=0.0), which is at index 0 in LTR order (should have audio URL).
        assert len(data) == 2
        
        # Panel B (idx 0 in RTL response)
        assert abs(data[0]["left"] - 0.5) < 1e-4
        assert data[0]["audioUrl"] is None
        
        # Panel A (idx 1 in RTL response)
        assert abs(data[1]["left"] - 0.0) < 1e-4
        assert data[1]["audioUrl"] == f"/api/audio/{comic_id}/{comic_id}_p0_panel0_narration.mp3"

    # Cleanup DB and file
    if os.path.exists(audio_path):
        os.remove(audio_path)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
    cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
    conn.commit()
    conn.close()


def test_pipeline_api_resilience():
    # Setup mock image
    img = Image.new("RGB", (100, 100))
    
    # Mock clients
    mock_nvidia_fail = MagicMock()
    mock_nvidia_fail.analyze_panel.side_effect = Exception("Nvidia connection failed")
    
    mock_audio_gen = MagicMock()
    mock_model_runner = MagicMock()
    mock_model_runner.run_inference.return_value = ([None], {})
    mock_decoder = MagicMock()
    mock_decoder.decode.return_value = {"panels": [], "bubbles": []}
    
    with patch("server.pipeline.pipeline.PanelPipeline.zoom_regions") as mock_zoom:
        mock_zoom.return_value = [Panel(0.0, 0.0, 1.0, 1.0)]
        
        # 1. Nvidia fail test
        conn = get_db_connection()
        cursor = conn.cursor()
        comic_id = "test-resilience-nvidia"
        cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
        cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
        cursor.execute(
            "INSERT INTO comics (id, title, file_path, total_pages) VALUES (?, ?, ?, ?)",
            (comic_id, "Test Resilient Comic", "test_file.zip", 1)
        )
        conn.commit()
        
        from server.pipeline.pipeline import process_page
        # Should not raise exception
        process_page(
            comic_id=comic_id,
            page_number=0,
            img=img,
            model_runner=mock_model_runner,
            decoder=mock_decoder,
            nvidia_client=mock_nvidia_fail,
            audio_generator=mock_audio_gen,
            db_conn=conn,
            rtl=False
        )
        
        cursor.execute("SELECT dialogue_text, sfx_description FROM panel_audio WHERE comic_id = ?", (comic_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "" # Defaulted to empty string
        assert row[1] == "" # Defaulted to empty string
        
        # 2. ElevenLabs fail test
        mock_nvidia_ok = MagicMock()
        mock_nvidia_ok.analyze_panel.return_value = {"dialogue": "Hello", "sfx": "Boom"}
        
        mock_audio_gen_fail = MagicMock()
        mock_audio_gen_fail.generate_tts.side_effect = Exception("ElevenLabs TTS failure")
        sfx_path = os.path.join("uploads", "audio", f"{comic_id}_p0_panel0_sfx.mp3")
        def side_effect_sfx(desc, path):
            with open(path, "wb") as f:
                f.write(b"sfx")
        mock_audio_gen_fail.generate_sfx.side_effect = side_effect_sfx
        
        cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
        conn.commit()
        
        process_page(
            comic_id=comic_id,
            page_number=0,
            img=img,
            model_runner=mock_model_runner,
            decoder=mock_decoder,
            nvidia_client=mock_nvidia_ok,
            audio_generator=mock_audio_gen_fail,
            db_conn=conn,
            rtl=False
        )
        
        cursor.execute("SELECT dialogue_text, sfx_description, audio_path, sfx_path FROM panel_audio WHERE comic_id = ?", (comic_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Hello"
        assert row[1] == "Boom"
        assert row[2] is None # Failed to generate TTS
        assert row[3] is not None # Succeeded in generating SFX
        
        # Cleanup
        if row[3] and os.path.exists(row[3]):
            os.remove(row[3])
        cursor.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
        cursor.execute("DELETE FROM panel_audio WHERE comic_id = ?", (comic_id,))
        conn.commit()
        conn.close()
