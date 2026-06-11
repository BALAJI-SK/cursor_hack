package com.chakra.comicreader.detection

/**
 * Sorts detected panels into reading order using a **recursive X-Y cut with straddle tolerance**.
 *
 * Comics are read in rows (top→bottom), and within a row left→right (Western) or right→left (manga).
 * At each step we look for a straight cut that separates the panels into two groups:
 *  - a **horizontal** cut (preferred) stacks the groups top→bottom — i.e. rows;
 *  - a **vertical** cut arranges them by reading direction — i.e. columns.
 * A panel is allowed to poke slightly across a cut (up to [STRADDLE_TOLERANCE] of its own length) and
 * is assigned to whichever side holds most of it — so a row of not-perfectly-aligned panels still
 * splits into one row. A panel that genuinely spans two rows (a tall panel beside stacked ones) makes
 * the horizontal cut impossible, so we cut vertically first — separating the tall panel from the
 * stack — then recurse, which is exactly the case a naive "group by row overlap" gets wrong.
 */
object PanelOrdering {

    /** A panel may cross a cut line by up to this fraction of its own height/width and still be
     *  assigned cleanly to one side (handles slightly misaligned panels in the same row). */
    private const val STRADDLE_TOLERANCE = 0.25f

    fun order(panels: List<Panel>, rightToLeft: Boolean = false): List<Panel> {
        if (panels.size <= 1) return panels
        return cut(panels, rightToLeft)
    }

    private fun cut(panels: List<Panel>, rightToLeft: Boolean): List<Panel> {
        if (panels.size <= 1) return panels

        // Prefer a horizontal cut → rows, read top to bottom.
        findCut(panels, vertical = false)?.let { (top, bottom) ->
            return cut(top, rightToLeft) + cut(bottom, rightToLeft)
        }

        // Otherwise a vertical cut → columns, read by direction (right group first for manga).
        findCut(panels, vertical = true)?.let { (left, right) ->
            return if (rightToLeft) cut(right, rightToLeft) + cut(left, rightToLeft)
            else cut(left, rightToLeft) + cut(right, rightToLeft)
        }

        // No clean cut (panels overlap both ways) → stable fallback by top then direction.
        return panels.sortedWith(
            if (rightToLeft) compareBy({ it.top }, { -it.left }) else compareBy({ it.top }, { it.left }),
        )
    }

    /**
     * Tries to split [panels] into two non-empty groups along one axis. [vertical] = false cuts
     * horizontally (returns top group, bottom group); true cuts vertically (left group, right group).
     * Scans candidate cut lines (panel trailing edges); a line is valid only if every panel sits on
     * one side or straddles by at most [STRADDLE_TOLERANCE] of its length. Returns null if no line works.
     */
    private fun findCut(panels: List<Panel>, vertical: Boolean): Pair<List<Panel>, List<Panel>>? {
        val start = { p: Panel -> if (vertical) p.left else p.top }
        val end = { p: Panel -> if (vertical) p.right else p.bottom }

        val maxEnd = panels.maxOf(end)
        val candidates = panels.map(end).distinct().sorted()
        for (line in candidates) {
            if (line >= maxEnd) continue // wouldn't leave anything below/right
            val first = mutableListOf<Panel>()  // top (or left) side
            val second = mutableListOf<Panel>() // bottom (or right) side
            var valid = true
            for (p in panels) {
                val s = start(p); val e = end(p)
                when {
                    e <= line -> first.add(p)
                    s >= line -> second.add(p)
                    else -> {
                        val len = (e - s).coerceAtLeast(1e-4f)
                        val crossDepth = minOf(e - line, line - s) // how far it pokes onto the thinner side
                        if (crossDepth / len > STRADDLE_TOLERANCE) { valid = false; break }
                        if (line - s >= e - line) first.add(p) else second.add(p) // majority side
                    }
                }
            }
            if (valid && first.isNotEmpty() && second.isNotEmpty()) return first to second
        }
        return null
    }
}
