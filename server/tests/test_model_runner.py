import pytest
from PIL import Image
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_runner import ModelRunner

def test_model_loading_and_inference():
    # Use relative path to find model asset
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "app/src/main/assets/manga_panel_detector_int8.tflite"
    )
    runner = ModelRunner(model_path)
    # Run inference on a blank 100x100 white image
    img = Image.new("RGB", (100, 100), color="white")
    raw_out, lb = runner.run_inference(img)
    
    assert raw_out.shape == (1, 300, 6)
    assert lb["scale"] == pytest.approx(6.4)
    assert lb["padX"] == 0
    assert lb["padY"] == 0
