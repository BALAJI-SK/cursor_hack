from .panel import Panel

class PanelGapFiller:
    def __init__(self, min_area_fraction=0.07, min_side_fraction=0.12, grid=64, max_fills=8):
        self.min_area_fraction = min_area_fraction
        self.min_side_fraction = min_side_fraction
        self.grid = grid
        self.max_fills = max_fills

    def fill(self, panels: list[Panel]) -> list[Panel]:
        if not panels:
            return panels
        n = self.grid
        covered = [False] * (n * n)
        for gy in range(n):
            cy = (gy + 0.5) / n
            for gx in range(n):
                cx = (gx + 0.5) / n
                covered[gy * n + gx] = any(
                    cx >= p.left and cx <= p.right and cy >= p.top and cy <= p.bottom for p in panels
                )

        cell_area = 1.0 / (n * n)
        gaps = []
        for _ in range(self.max_fills):
            rect = self._largest_empty_rectangle(covered, n)
            if not rect:
                break
            rect_cells, x0, y0, x1, y1 = rect
            if rect_cells * cell_area < self.min_area_fraction:
                break

            # Mark grid cells covered
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    covered[yy * n + xx] = True

            w_frac = (x1 - x0 + 1) / n
            h_frac = (y1 - y0 + 1) / n
            if w_frac >= self.min_side_fraction and h_frac >= self.min_side_fraction:
                gaps.append(Panel(x0 / n, y0 / n, (x1 + 1) / n, (y1 + 1) / n))

        return panels + gaps

    def _largest_empty_rectangle(self, covered: list[bool], n: int):
        height = [0] * n
        best = None # tuple: (cells, x0, y0, x1, y1)
        for y in range(n):
            for x in range(n):
                height[x] = 0 if covered[y * n + x] else height[x] + 1
            
            stack = []
            x = 0
            while x <= n:
                h = height[x] if x < n else 0
                while stack and height[stack[-1]] >= h:
                    bar_height = height[stack.pop()]
                    left = stack[-1] + 1 if stack else 0
                    right = x - 1
                    if bar_height > 0:
                        cells = bar_height * (right - left + 1)
                        if best is None or cells > best[0]:
                            best = (cells, left, y - bar_height + 1, right, y)
                if x < n:
                    stack.append(x)
                x += 1
        return best
