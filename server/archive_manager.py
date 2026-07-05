import os
import zipfile
import rarfile
from PIL import Image
import io

class ArchiveManager:
    def list_pages(self, path: str) -> list[str]:
        ext = os.path.splitext(path)[1].lower()
        if ext in [".cbz", ".zip"]:
            with zipfile.ZipFile(path, 'r') as z:
                names = z.namelist()
                return sorted([n for n in names if self._is_img(n)])
        elif ext in [".cbr", ".rar"]:
            with rarfile.RarFile(path, 'r') as r:
                names = r.namelist()
                return sorted([n for n in names if self._is_img(n)])
        return []

    def extract_page(self, path: str, page_name: str) -> bytes:
        ext = os.path.splitext(path)[1].lower()
        if ext in [".cbz", ".zip"]:
            with zipfile.ZipFile(path, 'r') as z:
                return z.read(page_name)
        elif ext in [".cbr", ".rar"]:
            with rarfile.RarFile(path, 'r') as r:
                return r.read(page_name)
        return b""

    def extract_cover_thumbnail(self, path: str) -> bytes:
        pages = self.list_pages(path)
        if not pages:
            return b""
        img_bytes = self.extract_page(path, pages[0])
        img = Image.open(io.BytesIO(img_bytes))
        img.thumbnail((300, 300))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=80)
        return out.getvalue()

    def _is_img(self, name: str) -> bool:
        base = os.path.basename(name)
        if base.startswith(".") or "__MACOSX" in name:
            return False
        ext = os.path.splitext(name)[1].lower()
        return ext in [".jpg", ".jpeg", ".png", ".webp"]
