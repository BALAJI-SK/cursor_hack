from .panel import Panel

class PanelPlanner:
    def __init__(self):
        self.small_area = 0.10
        self.big_area = 0.35
        self.square_aspect_low = 0.8
        self.square_aspect_high = 1.25
        self.adjacency_gap = 0.05
        self.adjacency_overlap = 0.4
        self.max_merge_count = 3
        self.max_merged_width = 0.55
        self.max_merged_height = 0.45
        self.cut_central_min = 0.30
        self.cut_central_max = 0.70
        self.full_width = 0.85
        self.broad_height = 0.55
        self.min_divide_height = 0.10
        self.spread_aspect_min = 1.15
        self.cross_page_width = 0.85
        self.spread_page_width = 0.42

    def plan(self, ordered: list[Panel], bubbles: list[Panel], pageW: int, pageH: int, rtl: bool) -> list[Panel]:
        if not ordered:
            return []
        page_aspect = pageW / pageH
        merged = self._merge_small(ordered)
        result = []
        for p, is_merged in merged:
            if not is_merged and self._should_divide(p, page_aspect):
                result.extend(self._divide(p, bubbles, page_aspect, rtl))
            else:
                result.append(p)
        return result

    def _merge_small(self, ordered: list[Panel]) -> list[tuple[Panel, bool]]:
        regions = []
        i = 0
        while i < len(ordered):
            cur = ordered[i]
            if cur.area >= self.small_area:
                regions.append((cur, False))
                i += 1
                continue
            union = cur
            j = i
            count = 1
            direction = "NONE"
            while j + 1 < len(ordered) and count < self.max_merge_count and ordered[j+1].area < self.small_area:
                next_p = ordered[j+1]
                step_dir = self._adjacency_dir(ordered[j], next_p)
                if step_dir == "NONE":
                    break
                if direction == "NONE":
                    direction = step_dir
                elif step_dir != direction:
                    break
                
                candidate = self._union(union, next_p)
                if candidate.width > self.max_merged_width or candidate.height > self.max_merged_height:
                    break
                union = candidate
                j += 1
                count += 1
            regions.append((union, count > 1))
            i = j + 1
        return regions

    def _should_divide(self, p: Panel, aspect: float) -> bool:
        spread = aspect >= self.spread_aspect_min
        if spread and p.width >= self.cross_page_width:
            return True
        is_full = p.width >= (self.spread_page_width if spread else self.full_width)
        if is_full and p.height >= self.min_divide_height:
            return True
        return p.area > self.big_area and not (self.square_aspect_low <= (p.width/p.height)*aspect <= self.square_aspect_high)

    def _divide(self, p: Panel, bubbles: list[Panel], aspect: float, rtl: bool) -> list[Panel]:
        spread = aspect >= self.spread_aspect_min
        if spread and p.width >= self.cross_page_width:
            rows = 2 if p.height >= self.broad_height else 1
            return self._grid_split(p, 4, rows, rtl)
        is_full = p.width >= (self.spread_page_width if spread else self.full_width)
        if is_full:
            inside = [b for b in bubbles if p.left <= b.centerX <= p.right and p.top <= b.centerY <= p.bottom]
            if p.height >= self.broad_height:
                # quarter (2x2)
                v_cut = self._cut_pos([b.left for b in inside], [b.right for b in inside], p.left, p.right)
                h_cut = self._cut_pos([b.top for b in inside], [b.bottom for b in inside], p.top, p.bottom)
                tl, tr = Panel(p.left, p.top, v_cut, h_cut), Panel(v_cut, p.top, p.right, h_cut)
                bl, br = Panel(p.left, h_cut, v_cut, p.bottom), Panel(v_cut, h_cut, p.right, p.bottom)
                return [tr, tl, br, bl] if rtl else [tl, tr, bl, br]
            else:
                # halve left-right
                v_cut = self._cut_pos([b.left for b in inside], [b.right for b in inside], p.left, p.right)
                l, r = Panel(p.left, p.top, v_cut, p.bottom), Panel(v_cut, p.top, p.right, p.bottom)
                return [r, l] if rtl else [l, r]
        
        # Classic divide
        inside = [b for b in bubbles if p.left <= b.centerX <= p.right and p.top <= b.centerY <= p.bottom]
        real_asp = (p.width / p.height) * aspect
        if real_asp >= self.square_aspect_high:
            v_cut = self._cut_pos([b.left for b in inside], [b.right for b in inside], p.left, p.right)
            l, r = Panel(p.left, p.top, v_cut, p.bottom), Panel(v_cut, p.top, p.right, p.bottom)
            return [r, l] if rtl else [l, r]
        else:
            h_cut = self._cut_pos([b.top for b in inside], [b.bottom for b in inside], p.top, p.bottom)
            return [Panel(p.left, p.top, p.right, h_cut), Panel(p.left, h_cut, p.right, p.bottom)]

      # grid split for double page spreads
    def _grid_split(self, p: Panel, cols: int, rows: int, rtl: bool) -> list[Panel]:
        cw = p.width / cols
        rh = p.height / rows
        pieces = []
        for r in range(rows):
            top = p.top if r == 0 else p.top + r * rh
            bottom = p.bottom if r == rows - 1 else p.top + (r + 1) * rh
            col_indices = range(cols - 1, -1, -1) if rtl else range(cols)
            for c in col_indices:
                left = p.left if c == 0 else p.left + c * cw
                right = p.right if c == cols - 1 else p.left + (c + 1) * cw
                pieces.append(Panel(left, top, right, bottom))
        return pieces

    def _cut_pos(self, lows: list[float], highs: list[float], start: float, end: float) -> float:
        center = (start + end) / 2.0
        lo = start + (end - start) * self.cut_central_min
        hi = start + (end - start) * self.cut_central_max
        if len(lows) >= 2:
            spans = sorted(zip(lows, highs), key=lambda x: x[0])
            best_gap = 0.0
            best_mid = center
            cursor = spans[0][1]
            for next_lo, next_hi in spans[1:]:
                gap = next_lo - cursor
                if gap > best_gap:
                    best_gap = gap
                    best_mid = (cursor + next_lo) / 2.0
                cursor = max(cursor, next_hi)
            if best_gap > 0.0 and lo <= best_mid <= hi:
                return best_mid
        return max(lo, min(hi, center))

    def _adjacency_dir(self, a: Panel, b: Panel) -> str:
        v_overlap = self._overlap(a.top, a.bottom, b.top, b.bottom) / max(1e-4, min(a.height, b.height))
        h_overlap = self._overlap(a.left, a.right, b.left, b.right) / max(1e-4, min(a.width, b.width))
        h_gap = max(0.0, max(a.left, b.left) - min(a.right, b.right))
        v_gap = max(0.0, max(a.top, b.top) - min(a.bottom, b.bottom))
        side_by_side = v_overlap >= self.adjacency_overlap and h_gap <= self.adjacency_gap
        stacked = h_overlap >= self.adjacency_overlap and v_gap <= self.adjacency_gap
        if side_by_side and stacked:
            return "HORIZONTAL" if h_gap <= v_gap else "VERTICAL"
        if side_by_side:
            return "HORIZONTAL"
        if stacked:
            return "VERTICAL"
        return "NONE"

    def _overlap(self, a0, a1, b0, b1) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    def _union(self, a: Panel, b: Panel) -> Panel:
        return Panel(min(a.left, b.left), min(a.top, b.top), max(a.right, b.right), max(a.bottom, b.bottom))
