# Design Spec: NVIDIA VLM & ElevenLabs Audio Integration

**Date**: 2026-07-05  
**Topic**: Voice Narration and Dynamic Action Sound Effects  
**Status**: APPROVED

---

## 1. Overview & Goals
The goal of this feature is to turn AGAM (Agam Katha Reader) into an immersive "motion-comic" reading experience. 
As the user steps through panels:
1. The app plays dynamic **Action Sound Effects** (like a sword slash, explosion, or laugh) matching the action in the panel.
2. The app plays a high-quality **Voice-Over Narration** of the speech bubble dialogue.
3. This is powered by **NVIDIA NIM VLM API** (for text & sound extraction) and **ElevenLabs APIs** (for voice and custom sound effects), with a **local SFX library** fallback to conserve API credits.

---

## 2. Architecture & Data Flow

```
+--------------------+      Cropped Panel      +----------------------+
|                    | ----------------------> |                      |
|   Comic Upload /   |                         |  NVIDIA VLM API      |
|   YOLO Detection   |      Text & SFX Tag     |  (Llama-3.2-Vision)  |
|                    | <---------------------- |                      |
+--------------------+                         +----------------------+
          |
          v
+--------------------+
|  Audio Generator   |
|  * ElevenLabs TTS  | ----------------------> Save Audio Files to
|  * ElevenLabs SFX  |                         /app/uploads/audio/
|  * Local SFX Match |
+--------------------+
          |
          v
+--------------------+
| SQLite Database    |
| (Paths & Metadata) |
+--------------------+
          |
          v
+--------------------+
| Frontend Reader    | <--- Audio URLs --- /api/comics/{id}/pages/{page}/panels
| (Auto-play on zoom)|
+--------------------+
```

---

## 3. Database Schema Updates
We will add a new table `panel_audio` in database.py:

```sql
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
```

---

## 4. Pipeline Processing Steps (Pre-Processing during Import)
During the background task for comic imports:
1. **YOLO Detection & Sorting**: Detect and order all panels on a page.
2. **Crop Panel**: Slice the page image based on the detected panel coordinates.
3. **NVIDIA VLM Call**:
   * Send the cropped panel image to NVIDIA NIM endpoint (`meta/llama-3.2-11b-vision-instruct`).
   * **System Prompt**: 
     > "You are a comic transcription assistant. Extract all dialogue from the speech bubbles in this panel. If there is an action or sound effect onomatopoeia written (e.g. 'SLASH', 'BOOM', 'GIGGLE'), output a 1-3 word description of that sound effect. Return JSON: { 'dialogue': '...', 'sfx': '...' }."
4. **Dialogue TTS**:
   * If `dialogue` text is returned: Call ElevenLabs TTS (`v1/text-to-speech`) using `ELEVEN_API_KEY`. Save the `.mp3` to `/app/uploads/audio/<comic_id>/page_<page>_panel_<index>.mp3`.
5. **Action SFX**:
   * If `sfx` is returned, check our local fallback mapping:
     * "slash" / "slice" / "knife" $\to$ `sfx/slash.mp3`
     * "boom" / "explosion" / "blast" $\to$ `sfx/boom.mp3`
     * "chuckle" / "gasp" / "laugh" $\to$ `sfx/chuckle.mp3`
     * "punch" / "hit" / "kick" $\to$ `sfx/punch.mp3`
     * "gasp" / "shock" $\to$ `sfx/gasp.mp3`
   * If matched locally, copy the asset path.
   * If it's a unique description, call ElevenLabs Sound Effects API (`v1/sound-effects`) to generate a custom clip, and save it to the audio folder.
6. **Save to SQLite**: Write the metadata and paths to `panel_audio`.

---

## 5. API Endpoint Additions
* **Panel Data Extension**: `/api/comics/{id}/pages/{page}/panels` will now perform a SQL JOIN with `panel_audio` to return `audioUrl` and `sfxUrl` for each panel (if available).
* **Audio Streaming**: Add `/api/audio/{comic_id}/{filename}` to stream generated audio files from the uploads directory.

---

## 6. Frontend Reader & Playback Orchestration
1. **Audio Manager in Reader**:
   * Track playing audio elements. When the slot changes, immediately run `.pause()` and clear the audio queue to prevent overlap.
   * If unmuted:
     1. If `sfxUrl` is present: Play the SFX clip first.
     2. If `audioUrl` is present: Play the dialogue narration.
2. **Floating Audio Control UI**:
   * Add a Speaker Button (Mute/Unmute) in the header.
   * Add settings toggles to turn "Voice Narrator" and "Action SFX" on or off individually.
   * Save choices in `localStorage`.

---

## 7. Spec Self-Review
1. **Placeholders**: None.
2. **Consistency**: Database schema matches the pipeline steps and API output structure.
3. **Scope**: Well-defined boundaries:
   * Backend: Database extension, NVIDIA NIM VLM service, ElevenLabs client, local assets.
   * Frontend: Audio state controls, playback hook.
