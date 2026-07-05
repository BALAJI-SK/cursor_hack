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

def test_nvidia_client_empty_api_key():
    client = NvidiaVlmClient("")
    respx_res = client.analyze_panel(b"fake_image_bytes")
    assert respx_res == {"dialogue": "", "sfx": ""}

@respx.mock
def test_nvidia_client_returns_json_string():
    client = NvidiaVlmClient("fake_key")
    respx.post("https://integrate.api.nvidia.com/v1/chat/completions").respond(
        json={
            "choices": [
                {"message": {"content": '{"dialogue": "Parsed!", "sfx": "gasp"}'}}
            ]
        }
    )
    respx_res = client.analyze_panel(b"fake_image_bytes")
    assert respx_res == {"dialogue": "Parsed!", "sfx": "gasp"}

@respx.mock
def test_nvidia_client_returns_invalid_json_string():
    client = NvidiaVlmClient("fake_key")
    respx.post("https://integrate.api.nvidia.com/v1/chat/completions").respond(
        json={
            "choices": [
                {"message": {"content": "Not a JSON string"}}
            ]
        }
    )
    respx_res = client.analyze_panel(b"fake_image_bytes")
    assert respx_res == {"dialogue": "Not a JSON string", "sfx": ""}

