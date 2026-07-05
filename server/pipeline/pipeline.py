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
