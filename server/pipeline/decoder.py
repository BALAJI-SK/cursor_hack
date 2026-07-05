import numpy as np
from .panel import Panel

class YoloPanelDecoder:
    def __init__(self, confidence_threshold=0.25, nms_iou=0.45, containment_threshold=0.6, min_area_fraction=0.008):
        self.confidence_threshold = confidence_threshold
        self.nms_iou = nms_iou
        self.containment_threshold = containment_threshold
        self.min_area = min_area_fraction * 640 * 640

    def decode(self, raw: np.ndarray, lb: dict) -> dict:
        # Detect coordinate scale: if maximum coordinate is <= 1.5, coordinates are normalized,
        # so we scale them up to the model input size (640) for NMS and area checks.
        max_coord = 0.0
        for i in range(raw.shape[0]):
            for j in range(4):
                val = abs(raw[i, j])
                if val > max_coord:
                    max_coord = val
        coord_scale = 640.0 if max_coord <= 1.5 else 1.0
        print(f"[DEBUG] max_coord: {max_coord:.3f}, coord_scale: {coord_scale}")

        panels_raw = []
        bubbles_raw = []

        print(f"\n[DEBUG] --- RAW YOLO DETECTIONS (Total candidates: {raw.shape[0]}) ---")
        for i in range(raw.shape[0]):
            score = raw[i, 4]
            cls = int(raw[i, 5])
            if score >= 0.05: # log anything above 0.05 for debugging
                print(f"  Class: {cls} (0=panel, 1=bubble), Score: {score:.3f}, Box: {raw[i, 0:4]}")
            
            # Lower threshold for panels to 0.15 globally to catch hand-drawn or less defined layouts.
            # Keep bubbles at default threshold since text bubbles are high-contrast and distinct.
            thresh = 0.15 if cls == 0 else self.confidence_threshold
            if score < thresh:
                continue
            
            box = raw[i, 0:5].copy() # x1, y1, x2, y2, score
            box[0:4] = box[0:4] * coord_scale
            if cls == 0:
                panels_raw.append(box)
            elif cls == 1:
                bubbles_raw.append(box)

        print(f"[DEBUG] Panels input to NMS: {len(panels_raw)}")
        suppressed_panels = self._suppress(panels_raw)
        print(f"[DEBUG] Panels kept after NMS: {len(suppressed_panels)}")
        for idx, box in enumerate(suppressed_panels):
            print(f"  Kept Panel {idx}: Score {box[4]:.3f}, Box: {box[0:4]}")

        panels = self._to_panels(suppressed_panels, lb, self.min_area)
        bubbles = self._to_panels(self._suppress(bubbles_raw), lb, 0.0)

        print(f"[DEBUG] Final output panels count: {len(panels)}")
        return {"panels": panels, "bubbles": bubbles}

    def _to_panels(self, boxes: list, lb: dict, min_area: float) -> list[Panel]:
        out = []
        pageW, pageH = lb["pageW"], lb["pageH"]
        for box in boxes:
            w = max(0.0, box[2] - box[0])
            h = max(0.0, box[3] - box[1])
            if w * h < min_area:
                continue
            l = clip((box[0] - lb["padX"]) / lb["scale"] / pageW, 0.0, 1.0)
            t = clip((box[1] - lb["padY"]) / lb["scale"] / pageH, 0.0, 1.0)
            r = clip((box[2] - lb["padX"]) / lb["scale"] / pageW, 0.0, 1.0)
            b = clip((box[3] - lb["padY"]) / lb["scale"] / pageH, 0.0, 1.0)
            if r > l and b > t:
                out.append(Panel(l, t, r, b))
        return out

    def _suppress(self, boxes: list) -> list:
        sorted_boxes = sorted(boxes, key=lambda x: x[4], reverse=True)
        kept = []
        for box in sorted_boxes:
            redundant = False
            for k in kept:
                # Check standard overlap (IoU)
                if self._iou(k, box) > self.nms_iou:
                    redundant = True
                    break
                # Check if the new box is contained inside an existing kept box 'k'
                if self._contained_fraction(box, k) > self.containment_threshold:
                    redundant = True
                    break
                # Check if the existing kept box 'k' is contained inside the new box
                if self._contained_fraction(k, box) > self.containment_threshold:
                    # If the engulfing new box has low confidence (< 0.25),
                    # we discard the new box to protect the high-confidence panel 'k'.
                    if box[4] < 0.25:
                        redundant = True
                        break
            if redundant:
                continue
            
            # Evict kept boxes contained inside the new larger box
            kept = [k for k in kept if self._contained_fraction(k, box) <= self.containment_threshold]
            kept.append(box)
        return kept

    def _iou(self, a, b) -> float:
        ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
        iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
        inter = ix * iy
        areaA = (a[2] - a[0]) * (a[3] - a[1])
        areaB = (b[2] - b[0]) * (b[3] - b[1])
        union = areaA + areaB - inter
        return inter / union if union > 0.0 else 0.0

    def _contained_fraction(self, inner, outer) -> float:
        ix = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
        iy = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
        inter = ix * iy
        inner_area = (inner[2] - inner[0]) * (inner[3] - inner[1])
        return inter / inner_area if inner_area > 0.0 else 0.0

def clip(val, low, high):
    return max(low, min(high, val))
