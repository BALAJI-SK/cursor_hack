import os
import uuid
from io import BytesIO
from PIL import Image

from .panel import Panel
from .gap_filler import PanelGapFiller
from .ordering import PanelOrdering
from .planner import PanelPlanner

class PanelPipeline:
    @staticmethod
    def zoom_regions(panels: list[Panel], bubbles: list[Panel], pageW: int, pageH: int, rightToLeft: bool) -> list[Panel]:
        filled = PanelGapFiller().fill(panels)
        ordered = PanelOrdering.order(filled, rightToLeft)
        planned = PanelPlanner().plan(ordered, bubbles, pageW, pageH, rightToLeft)
        if len(planned) >= 2:
            return planned
        return PanelPlanner().plan([Panel(0.0, 0.0, 1.0, 1.0)], bubbles, pageW, pageH, rightToLeft)


def process_page(
    comic_id: str,
    page_number: int,
    img: Image.Image,
    model_runner,
    decoder,
    nvidia_client,
    audio_generator,
    db_conn,
    rtl: bool = False
):
    # Run inference and get zoom regions
    raw_out, lb = model_runner.run_inference(img)
    decoded = decoder.decode(raw_out[0], lb)
    regions = PanelPipeline.zoom_regions(decoded["panels"], decoded["bubbles"], img.width, img.height, rtl)
    
    audio_dir = "uploads/audio"
    os.makedirs(audio_dir, exist_ok=True)
    pageW, pageH = img.size
    
    cursor = db_conn.cursor()
    
    for panel_index, p in enumerate(regions):
        box = (p.left * pageW, p.top * pageH, p.right * pageW, p.bottom * pageH)
        cropped_img = img.crop(box)
        
        buf = BytesIO()
        cropped_img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()
        
        # Call NVIDIA VLM to extract dialogue and sfx description
        try:
            analysis = nvidia_client.analyze_panel(image_bytes)
            dialogue_text = analysis.get("dialogue", "")
            sfx_description = analysis.get("sfx", "")
        except Exception as e:
            print(f"[WARNING] NVIDIA VLM call failed for panel {panel_index}: {e}")
            dialogue_text = ""
            sfx_description = ""
        
        audio_filename = f"{comic_id}_p{page_number}_panel{panel_index}_narration.mp3"
        sfx_filename = f"{comic_id}_p{page_number}_panel{panel_index}_sfx.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        sfx_path = os.path.join(audio_dir, sfx_filename)
        
        # Call ElevenLabs to generate TTS
        if dialogue_text:
            try:
                audio_generator.generate_tts(dialogue_text, audio_path)
                if not os.path.exists(audio_path):
                    audio_path = None
            except Exception as e:
                print(f"[WARNING] ElevenLabs TTS call failed for panel {panel_index}: {e}")
                audio_path = None
        else:
            audio_path = None
            
        # Call ElevenLabs to generate SFX
        if sfx_description:
            try:
                audio_generator.generate_sfx(sfx_description, sfx_path)
                if not os.path.exists(sfx_path):
                    sfx_path = None
            except Exception as e:
                print(f"[WARNING] ElevenLabs SFX call failed for panel {panel_index}: {e}")
                sfx_path = None
        else:
            sfx_path = None
            
        # Index paths inside panel_audio DB table
        cursor.execute("""
            INSERT OR REPLACE INTO panel_audio (id, comic_id, page_number, panel_index, dialogue_text, sfx_description, audio_path, sfx_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{comic_id}_{page_number}_{panel_index}",
            comic_id,
            page_number,
            panel_index,
            dialogue_text,
            sfx_description,
            audio_path,
            sfx_path
        ))
        
    db_conn.commit()
