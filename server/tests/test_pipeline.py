import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.panel import Panel
from pipeline.decoder import YoloPanelDecoder
from pipeline.gap_filler import PanelGapFiller
from pipeline.ordering import PanelOrdering
from pipeline.planner import PanelPlanner
from pipeline.pipeline import PanelPipeline

# --- PanelOrdering Tests ---
def test_ordering_rows_top_down_then_left_to_right():
    topLeft = Panel(0.0, 0.0, 0.45, 0.4)
    topRight = Panel(0.55, 0.0, 1.0, 0.4)
    bottomLeft = Panel(0.0, 0.5, 0.45, 1.0)
    bottomRight = Panel(0.55, 0.5, 1.0, 1.0)

    shuffled = [bottomRight, topRight, bottomLeft, topLeft]
    ordered = PanelOrdering.order(shuffled)
    assert ordered == [topLeft, topRight, bottomLeft, bottomRight]

def test_ordering_rtl_reverses_within_rows_only():
    topLeft = Panel(0.0, 0.0, 0.45, 0.4)
    topRight = Panel(0.55, 0.0, 1.0, 0.4)
    bottomLeft = Panel(0.0, 0.5, 0.45, 1.0)
    bottomRight = Panel(0.55, 0.5, 1.0, 1.0)

    shuffled = [bottomRight, topRight, bottomLeft, topLeft]
    ordered = PanelOrdering.order(shuffled, right_to_left=True)
    assert ordered == [topRight, topLeft, bottomRight, bottomLeft]

def test_ordering_slightly_misaligned_panels_share_row():
    left = Panel(0.0, 0.10, 0.45, 0.45)
    right = Panel(0.55, 0.05, 1.0, 0.40)
    ordered = PanelOrdering.order([right, left])
    assert ordered == [left, right]

# --- PanelGapFiller Tests ---
def test_gap_filler_empty_input():
    assert PanelGapFiller().fill([]) == []

def test_gap_filler_big_rectangular_leftover():
    top = Panel(0.0, 0.0, 1.0, 0.40)
    result = PanelGapFiller().fill([top])
    assert len(result) == 2
    gap = result[-1]
    assert 0.35 <= gap.top <= 0.45
    assert gap.bottom >= 0.95
    assert gap.width >= 0.95

# --- PanelPlanner Tests ---
def test_planner_empty_input():
    assert PanelPlanner().plan([], [], 1000, 1000, False) == []

def test_planner_merges_small_panels():
    # Two small adjacent panels: both area < 10%
    p1 = Panel(0.1, 0.1, 0.25, 0.25)
    p2 = Panel(0.26, 0.1, 0.4, 0.25)
    
    # Run pipeline with custom config inside planner to check merging
    planner = PanelPlanner()
    planner.small_area = 0.15 # make sure 0.15 * 0.15 = 0.0225 area is small
    res = planner.plan([p1, p2], [], 1000, 1000, False)
    assert len(res) == 1
    # Merged bounding box
    assert res[0].left == 0.1
    assert res[0].right == 0.4
