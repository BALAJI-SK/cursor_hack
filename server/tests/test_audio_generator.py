from server.pipeline.audio_generator import AudioGenerator
import os
import tempfile
import pytest
import respx
import httpx
import shutil

# Fixture to ensure placeholder directory and files exist for tests
@pytest.fixture(autouse=True)
def setup_sfx_assets():
    os.makedirs("server/assets/sfx", exist_ok=True)
    placeholders = {
        "slash.mp3": b"fake_slash_mp3",
        "boom.mp3": b"fake_boom_mp3",
        "chuckle.mp3": b"fake_chuckle_mp3",
        "punch.mp3": b"fake_punch_mp3",
        "gasp.mp3": b"fake_gasp_mp3",
    }
    for filename, content in placeholders.items():
        with open(os.path.join("server/assets/sfx", filename), "wb") as f:
            f.write(content)

def test_local_sfx_mapping_exact():
    gen = AudioGenerator("fake_key")
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        
        # Test direct mapping
        gen.generate_sfx("chuckle", out_file)
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            assert f.read() == b"fake_chuckle_mp3"

def test_local_sfx_mapping_variations():
    gen = AudioGenerator("fake_key")
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        
        # Test case insensitivity and mapping synonyms (knife -> slash)
        gen.generate_sfx("A sharp KNIFE slice", out_file)
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            assert f.read() == b"fake_slash_mp3"

def test_local_sfx_mapping_punch_synonym():
    gen = AudioGenerator("fake_key")
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        
        # Test synonyms (hit -> punch)
        gen.generate_sfx("He got hit by a car", out_file)
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            assert f.read() == b"fake_punch_mp3"

@respx.mock
def test_generate_sfx_api_fallback():
    gen = AudioGenerator("fake_api_key")
    
    # Mock sound generation API
    respx.post("https://api.elevenlabs.io/v1/sound-generation").respond(
        status_code=200,
        content=b"elevenlabs_generated_sfx_bytes"
    )
    
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        # "laser beam" does not match any local keywords (slash, boom, chuckle, punch, gasp, etc.)
        gen.generate_sfx("pew pew laser beam", out_file)
        
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            assert f.read() == b"elevenlabs_generated_sfx_bytes"

def test_generate_sfx_no_key_no_match():
    gen = AudioGenerator("")
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        # Does not match local keywords and no api key is present
        gen.generate_sfx("pew pew laser beam", out_file)
        assert not os.path.exists(out_file)

@respx.mock
def test_generate_tts_success():
    gen = AudioGenerator("fake_api_key")
    
    # Mock text-to-speech API
    respx.post("https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM").respond(
        status_code=200,
        content=b"elevenlabs_tts_bytes"
    )
    
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        gen.generate_tts("Hello world", out_file)
        
        assert os.path.exists(out_file)
        with open(out_file, "rb") as f:
            assert f.read() == b"elevenlabs_tts_bytes"

def test_generate_tts_no_key():
    gen = AudioGenerator("")
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        gen.generate_tts("Hello world", out_file)
        assert not os.path.exists(out_file)

@respx.mock
def test_generate_sfx_api_error():
    gen = AudioGenerator("fake_api_key")
    
    # Mock API failure
    respx.post("https://api.elevenlabs.io/v1/sound-generation").respond(
        status_code=400
    )
    
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        with pytest.raises(httpx.HTTPStatusError):
            gen.generate_sfx("pew pew laser beam", out_file)

@respx.mock
def test_generate_tts_api_error():
    gen = AudioGenerator("fake_api_key")
    
    # Mock API failure
    respx.post("https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM").respond(
        status_code=500
    )
    
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "out.mp3")
        with pytest.raises(httpx.HTTPStatusError):
            gen.generate_tts("Hello world", out_file)
