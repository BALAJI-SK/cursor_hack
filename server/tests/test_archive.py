import os
import zipfile
import pytest
from PIL import Image
import io
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from archive_manager import ArchiveManager

def test_zip_archive_reading(tmp_path):
    # Create mock CBZ
    cbz_path = tmp_path / "test.cbz"
    with zipfile.ZipFile(cbz_path, 'w') as z:
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        z.writestr("page1.jpg", img_bytes.getvalue())
        z.writestr("page2.png", img_bytes.getvalue())
        z.writestr("not_an_image.txt", b"hello world")

    manager = ArchiveManager()
    pages = manager.list_pages(str(cbz_path))
    assert len(pages) == 2
    assert pages[0] == "page1.jpg"
    assert pages[1] == "page2.png"
    
    extracted = manager.extract_page(str(cbz_path), "page1.jpg")
    assert len(extracted) > 0
    
    cover = manager.extract_cover_thumbnail(str(cbz_path))
    assert len(cover) > 0
