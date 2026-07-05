import httpx
import os
import shutil

class AudioGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tts_url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        self.sfx_url = "https://api.elevenlabs.io/v1/sound-generation"
        
        # Keyword mapping to pre-seeded local SFX files
        self.local_sfx = {
            "slash": "server/assets/sfx/slash.mp3",
            "slice": "server/assets/sfx/slash.mp3",
            "knife": "server/assets/sfx/slash.mp3",
            "boom": "server/assets/sfx/boom.mp3",
            "explosion": "server/assets/sfx/boom.mp3",
            "chuckle": "server/assets/sfx/chuckle.mp3",
            "laugh": "server/assets/sfx/chuckle.mp3",
            "giggle": "server/assets/sfx/chuckle.mp3",
            "punch": "server/assets/sfx/punch.mp3",
            "hit": "server/assets/sfx/punch.mp3",
            "gasp": "server/assets/sfx/gasp.mp3",
            "shock": "server/assets/sfx/gasp.mp3"
        }

    def generate_tts(self, text: str, out_path: str):
        if not self.api_key:
            return
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_monolingual_v1"}
        res = httpx.post(self.tts_url, headers=headers, json=payload, timeout=20.0)
        res.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(res.content)

    def generate_sfx(self, desc: str, out_path: str):
        # Local library matching check
        desc_lower = desc.lower()
        for kw, local_path in self.local_sfx.items():
            if kw in desc_lower:
                # To be robust, check if the path exists relative to current dir,
                # or relative to the parent directory of this script's directory.
                resolved_path = local_path
                if not os.path.exists(resolved_path):
                    # Try resolving relative to this script's directory
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    # script_dir is server/pipeline, so parent is server/, grandparent is root.
                    grandparent_dir = os.path.dirname(os.path.dirname(script_dir))
                    alt_path = os.path.join(grandparent_dir, local_path)
                    if os.path.exists(alt_path):
                        resolved_path = alt_path
                
                if os.path.exists(resolved_path):
                    shutil.copy(resolved_path, out_path)
                    return
        
        # Fallback to ElevenLabs Sound Generation API
        if not self.api_key:
            return
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"text": desc}
        res = httpx.post(self.sfx_url, headers=headers, json=payload, timeout=25.0)
        res.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(res.content)
