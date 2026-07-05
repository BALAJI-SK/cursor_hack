from server.database import get_db_connection, init_db

def test_panel_audio_schema():
    # Force init
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    # Inspect columns
    cursor.execute("PRAGMA table_info(panel_audio);")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    assert "comic_id" in columns
    assert "audio_path" in columns
    assert "sfx_path" in columns
    conn.close()

