# Comic Narration & Sound Effects (SFX) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate NVIDIA VLM for dialogue extraction and ElevenLabs TTS/SFX for immersive, panel-by-panel reading and audio effects.

**Architecture:** Extend backend to crop panel bounding boxes and call NVIDIA's VLM endpoint to transcribe text/describe action sounds. Generate corresponding speech/sfx `.mp3` files via ElevenLabs or local fallback matching, index them in SQLite, and play them on-demand inside the glassmorphic React reader based on user muting preferences.

**Tech Stack:** FastAPI, SQLite, PIL (Pillow), HTTPX, React, Web Audio API, ElevenLabs API, NVIDIA NIM VLM API.

## Global Constraints
* No external global library dependencies beyond standard packages (HTTPX).
* Keep all new SQLite queries parameterized.
* All audio files must be stored relative to the persistent `/app/uploads/audio` directory.
* React settings for muting must persist in `localStorage`.

---

### Task 1: Database Migration & Schema Setup

**Files:**
- Modify: `server/database.py`
- Test: `server/tests/test_database.py`

**Interfaces:**
- Produces: `init_db()` (updated to include `panel_audio` schema)

- [ ] **Step 1: Write the database schema update**
  
  Add `panel_audio` table creation logic in [server/database.py](file:///Users/balajisk/cursor_hackthon/AGAM/server/database.py):
  ```python
  # In database.py, inside the init_db() SQL commands block
  cursor.execute("""
  CREATE TABLE IF NOT EXISTS panel_audio (
      id TEXT PRIMARY KEY,
      comic_id TEXT NOT NULL,
      page_number INTEGER NOT NULL,
      panel_index INTEGER NOT NULL,
      dialogue_text TEXT,
      sfx_description TEXT,
      audio_path TEXT,
      sfx_path TEXT,
      FOREIGN KEY(comic_id) REFERENCES comics(id) ON DELETE CASCADE
  );
  """)
  ```

- [ ] **Step 2: Create a schema validation unit test**
  
  Write a test in `server/tests/test_database.py`:
  ```python
  import sqlite3
  from server.database import get_db_connection, init_db

  def test_panel_audio_schema():
      # Force init
      conn = get_db_connection()
      cursor = conn.cursor()
      init_db()
      # Inspect columns
      cursor.execute("PRAGMA table_info(panel_audio);")
      columns = {row[1]: row[2] for row in cursor.fetchall()}
      assert "comic_id" in columns
      assert "audio_path" in columns
      assert "sfx_path" in columns
      conn.close()
  ```

- [ ] **Step 3: Run database tests**
  
  Run: `pytest server/tests/test_database.py -v`  
  Expected: PASS

- [ ] **Step 4: Commit**
  
  Run:
  ```bash
  git add server/database.py
  git commit -m "feat(db): add panel_audio schema and unit test"
  ```

---

### Task 2: NVIDIA NIM VLM Client Integration

**Files:**
- Create: `server/pipeline/nvidia_client.py`
- Test: `server/tests/test_nvidia_client.py`

**Interfaces:**
- Produces: `NvidiaVlmClient(api_key: str).analyze_panel(image_bytes: bytes) -> dict`

- [ ] **Step 1: Create the VLM client class**
  
  Write the HTTP client in `server/pipeline/nvidia_client.py`:
  ```python
  import httpx
  import base64

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
          return response.json()["choices"][0]["message"]["content"]
  ```

- [ ] **Step 2: Write tests for client**
  
  Write a test in `server/tests/test_nvidia_client.py`:
  ```python
  from server.pipeline.nvidia_client import NvidiaVlmClient
  import respx
  import httpx

  @respx.mock
  def test_nvidia_client_returns_metadata():
      client = NvidiaVlmClient("fake_key")
      respx.post("https://integrate.api.nvidia.com/v1/chat/completions").respond(
          json={
              "choices": [
                  {"message": {"content": {"dialogue": "Hello!", "sfx": "chuckle"}}}
              ]
          }
      )
      respx_res = client.analyze_panel(b"fake_image_bytes")
      assert respx_res == {"dialogue": "Hello!", "sfx": "chuckle"}
  ```

- [ ] **Step 3: Run the client tests**
  
  Run: `pytest server/tests/test_nvidia_client.py -v`  
  Expected: PASS

- [ ] **Step 4: Commit**
  
  Run:
  ```bash
  git add server/pipeline/nvidia_client.py
  git commit -m "feat(pipeline): add nvidia nim vlm client wrapper"
  ```

---

### Task 3: ElevenLabs Audio Generator & SFX Fallback Library

**Files:**
- Create: `server/pipeline/audio_generator.py`
- Test: `server/tests/test_audio_generator.py`
- Add Assets: `server/assets/sfx/slash.mp3`, `server/assets/sfx/boom.mp3`, `server/assets/sfx/chuckle.mp3`, `server/assets/sfx/punch.mp3`, `server/assets/sfx/gasp.mp3`

**Interfaces:**
- Produces: `AudioGenerator(eleven_key: str).generate_tts(text: str, out_path: str)`
- Produces: `AudioGenerator(eleven_key: str).generate_sfx(desc: str, out_path: str)`

- [ ] **Step 1: Create standard placeholder local sfx files**
  
  We need to seed a folder for common sounds so that we don't call the ElevenLabs API for simple effects. Make the folders:
  `mkdir -p server/assets/sfx`
  Create dummy sound effect files for local development/testing (you can use small binary assets or placeholders).

- [ ] **Step 2: Write ElevenLabs Audio Generator class**
  
  Write the class in `server/pipeline/audio_generator.py`:
  ```python
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
              if kw in desc_lower and os.path.exists(local_path):
                  shutil.copy(local_path, out_path)
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
  ```

- [ ] **Step 3: Write tests for client**
  
  Write a test in `server/tests/test_audio_generator.py`:
  ```python
  from server.pipeline.audio_generator import AudioGenerator
  import os
  import tempfile

  def test_local_sfx_mapping():
      gen = AudioGenerator("fake_key")
      # Seed a fake local file
      os.makedirs("server/assets/sfx", exist_ok=True)
      with open("server/assets/sfx/boom.mp3", "wb") as f:
          f.write(b"fake_sfx_mp3")
          
      with tempfile.TemporaryDirectory() as tmp:
          out_file = os.path.join(tmp, "out.mp3")
          gen.generate_sfx("Huge explosion!", out_file)
          assert os.path.exists(out_file)
          with open(out_file, "rb") as f:
              assert f.read() == b"fake_sfx_mp3"
  ```

- [ ] **Step 4: Run the audio tests**
  
  Run: `pytest server/tests/test_audio_generator.py -v`  
  Expected: PASS

- [ ] **Step 5: Commit**
  
  Run:
  ```bash
  git add server/pipeline/audio_generator.py
  git commit -m "feat(pipeline): add elevenlabs audio generator and local sfx check"
  ```

---

### Task 4: Pipeline Integration & Audio Routes

**Files:**
- Modify: `server/pipeline/pipeline.py`
- Modify: `server/main.py`
- Test: `server/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `NvidiaVlmClient`, `AudioGenerator`
- Produces: `/api/audio/{comic_id}/{filename}` (Audio streamer route)

- [ ] **Step 1: Integrate VLM and ElevenLabs into Pipeline**
  
  Update `process_page` in `server/pipeline/pipeline.py` to:
  * Crop the panel using Pillow:
    ```python
    # In server/pipeline/pipeline.py inside the panel iteration
    # Crop: panel dimensions are normalized coords [0.0 - 1.0]
    box = (p.left * pageW, p.top * pageH, p.right * pageW, p.bottom * pageH)
    cropped_img = img.crop(box)
    
    # Save crop to bytes in memory
    from io import BytesIO
    buf = BytesIO()
    cropped_img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()
    ```
  * Call `NvidiaVlmClient` to extract `dialogue` and `sfx`.
  * Call `AudioGenerator` to render the narrator voice and trigger the sound effect file.
  * Index paths inside `panel_audio` DB table.

- [ ] **Step 2: Add API streaming and updated panel endpoints**
  
  Modify [server/main.py](file:///Users/balajisk/cursor_hackthon/AGAM/server/main.py) to:
  * Add endpoint `/api/audio/{comic_id}/{filename}` to stream `.mp3` files from `/app/uploads/audio/`.
  * Update `/api/comics/{comic_id}/pages/{page}/panels` to join `panel_audio` and return:
    `"audioUrl"` and `"sfxUrl"`.

- [ ] **Step 3: Run pipeline test suite**
  
  Run: `pytest server/tests/test_api.py -v`  
  Expected: PASS

- [ ] **Step 4: Commit**
  
  Run:
  ```bash
  git add server/pipeline/pipeline.py server/main.py
  git commit -m "feat(api): connect pipeline processing to DB and add streaming endpoints"
  ```

---

### Task 5: Frontend Audio Manager & Header Toggles

**Files:**
- Modify: `frontend/src/components/Reader.tsx`
- Modify: `frontend/src/components/Theme.css`

**Interfaces:**
- Consumes: `/api/comics/{id}/pages/{page}/panels` (returned `audioUrl` and `sfxUrl`)

- [ ] **Step 1: Add sound settings popover and volume controls**
  
  Add floating state variables to `Reader.tsx`:
  - `isMuted` (default: `false` / localstorage)
  - `enableNarrator` (default: `true` / localstorage)
  - `enableSfx` (default: `true` / localstorage)
  Add UI toggles to the floating glassmorphic header (e.g. Mute/Unmute icon button).

- [ ] **Step 2: Add audio manager playback orchestration**
  
  In the `useEffect` listening to `slot` changes:
  * Call `stop()` on any currently playing audio.
  * If `isMuted` is `false`:
    * If `sfxUrl` is present and `enableSfx` is `true`: play sfx.
    * If `audioUrl` is present and `enableNarrator` is `true`: play dialogue text.

- [ ] **Step 3: Verify the build**
  
  Run: `cd frontend && npm run build`  
  Expected: SUCCESS

- [ ] **Step 4: Commit**
  
  Run:
  ```bash
  git add frontend/src/components/Reader.tsx
  git commit -m "feat(ui): add reader audio settings toggles and playback manager"
  ```
