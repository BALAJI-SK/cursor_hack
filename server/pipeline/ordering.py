from .panel import Panel

class PanelOrdering:
    STRADDLE_TOLERANCE = 0.25
    ROW_BAND = 0.12

    @classmethod
    def order(cls, panels: list[Panel], right_to_left: bool = False) -> list[Panel]:
        if len(panels) <= 1:
            return panels
        return cls._cut(panels, right_to_left)

    @classmethod
    def _cut(cls, panels: list[Panel], rtl: bool) -> list[Panel]:
        if len(panels) <= 1:
            return panels

        # Prefer horizontal cut -> rows
        h_cut = cls._find_cut(panels, vertical=False)
        if h_cut:
            top, bottom = h_cut
            return cls._cut(top, rtl) + cls._cut(bottom, rtl)

        # Vertical cut
        v_cut = cls._find_cut(panels, vertical=True)
        if v_cut:
            left, right = v_cut
            return cls._cut(right, rtl) + cls._cut(left, rtl) if rtl else cls._cut(left, rtl) + cls._cut(right, rtl)

        # Fallback: group into row bands
        by_top = sorted(panels, key=lambda p: p.top)
        rows = []
        for p in by_top:
            if rows and (p.top - rows[-1][0].top <= cls.ROW_BAND):
                rows[-1].append(p)
            else:
                rows.append([p])
        
        out = []
        for row in rows:
            out.extend(sorted(row, key=lambda p: p.left, reverse=rtl))
        return out

    @classmethod
    def _find_cut(cls, panels: list[Panel], vertical: bool):
        start_fn = lambda p: p.left if vertical else p.top
        end_fn = lambda p: p.right if vertical else p.bottom

        max_end = max(end_fn(p) for p in panels)
        candidates = sorted(list(set(end_fn(p) for p in panels)))
        for line in candidates:
            if line >= max_end:
                continue
            first, second = [], []
            valid = True
            for p in panels:
                s, e = start_fn(p), end_fn(p)
                if e <= line:
                    first.append(p)
                elif s >= line:
                    second.append(p)
                else:
                    length = max(1e-4, e - s)
                    cross_depth = min(e - line, line - s)
                    if cross_depth / length > cls.STRADDLE_TOLERANCE:
                        valid = False
                        break
                    if line - s >= e - line:
                        first.append(p)
                      # majority side
                    else:
                        second.append(p)
            if valid and first and second:
                return first, second
        return None
