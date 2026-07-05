import httpx
import base64
import json

class NvidiaVlmClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def analyze_panel(self, image_bytes: bytes) -> dict:
        if not self.api_key:
            return {"dialogue": "", "sfx": ""}
        
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "meta/llama-3.2-11b-vision-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all dialogue inside speech bubbles in this panel. If there is an action onomatopoeia written (e.g. 'SLASH', 'BOOM', 'GIGGLE'), provide a 1-3 word description of that sound effect. Return JSON: { 'dialogue': '...', 'sfx': '...' }"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        response = httpx.post(self.url, headers=headers, json=payload, timeout=20.0)
        response.raise_for_status()
        
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"dialogue": content, "sfx": ""}
        return content
