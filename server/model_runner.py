import numpy as np
from PIL import Image
import tensorflow.lite as tflite
import threading

class ModelRunner:
    def __init__(self, model_path: str):
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.lock = threading.Lock()

    def run_inference(self, image: Image.Image) -> tuple[np.ndarray, dict]:
        pageW, pageH = image.size
        input_size = 640
        scale = min(input_size / pageW, input_size / pageH)
        newW, newH = max(1, int(pageW * scale)), max(1, int(pageH * scale))
        
        # Letterbox: resize preserving aspect, pad with gray-114
        resized = image.resize((newW, newH), Image.BILINEAR)
        padded = Image.new("RGB", (input_size, input_size), color=(114, 114, 114))
        padX = (input_size - newW) // 2
        padY = (input_size - newH) // 2
        padded.paste(resized, (padX, padY))

        # Preprocess: float32, normalize [0, 1], add batch dim
        img_data = np.array(padded, dtype=np.float32) / 255.0
        img_data = np.expand_dims(img_data, axis=0)

        with self.lock:
            self.interpreter.set_tensor(self.input_details[0]['index'], img_data)
            self.interpreter.invoke()
            raw_output = self.interpreter.get_tensor(self.output_details[0]['index']).copy()

        return raw_output, {
            "scale": scale,
            "padX": padX,
            "padY": padY,
            "newW": newW,
            "newH": newH,
            "pageW": pageW,
            "pageH": pageH
        }
