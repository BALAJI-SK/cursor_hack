import httpx
import os
import shutil

class AudioGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tts_url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        self.sfx_url = "https://api.elevenlabs.io/v1/sound-generation"
        self.sfx_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "sfx"))
        
        # Keyword mapping to pre-seeded local SFX files (filenames only)
        self.local_sfx = {
            "slash": "slash.mp3",
            "slice": "slash.mp3",
            "knife": "slash.mp3",
            "boom": "boom.mp3",
            "explosion": "boom.mp3",
            "chuckle": "chuckle.mp3",
            "laugh": "chuckle.mp3",
            "giggle": "chuckle.mp3",
            "punch": "punch.mp3",
            "hit": "punch.mp3",
            "gasp": "gasp.mp3",
            "shock": "gasp.mp3"
        }

    def generate_tts(self, text: str, out_path: str):
        if not self.api_key:
            return
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_monolingual_v1"}
        res = httpx.post(self.tts_url, headers=headers, json=payload, timeout=20.0)
        res.raise_for_status()
        
        dir_name = os.path.dirname(out_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(out_path, "wb") as f:
            f.write(res.content)

    def generate_sfx(self, desc: str, out_path: str):
        # Local library matching check
        desc_lower = desc.lower()
        for kw, filename in self.local_sfx.items():
            if kw in desc_lower:
                resolved_path = os.path.join(self.sfx_dir, filename)
                if os.path.exists(resolved_path):
                    dir_name = os.path.dirname(out_path)
                    if dir_name:
                        os.makedirs(dir_name, exist_ok=True)
                    shutil.copy(resolved_path, out_path)
                    return
        
        # Fallback to ElevenLabs Sound Generation API
        if not self.api_key:
            return
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"text": desc}
        res = httpx.post(self.sfx_url, headers=headers, json=payload, timeout=25.0)
        res.raise_for_status()
        
        dir_name = os.path.dirname(out_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(out_path, "wb") as f:
            f.write(res.content)

