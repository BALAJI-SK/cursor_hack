package com.chakra.comicreader.detection

import kotlin.test.Test
import kotlin.test.assertEquals

class PanelOrderingTest {

    private val topLeft = Panel(0.0f, 0.0f, 0.45f, 0.4f)
    private val topRight = Panel(0.55f, 0.0f, 1.0f, 0.4f)
    private val bottomLeft = Panel(0.0f, 0.5f, 0.45f, 1.0f)
    private val bottomRight = Panel(0.55f, 0.5f, 1.0f, 1.0f)

    @Test
    fun ordersRowsTopDownThenLeftToRight() {
        val shuffled = listOf(bottomRight, topRight, bottomLeft, topLeft)
        val ordered = PanelOrdering.order(shuffled)
        assertEquals(listOf(topLeft, topRight, bottomLeft, bottomRight), ordered)
    }

    @Test
    fun rightToLeftReversesWithinRowsOnly() {
        val shuffled = listOf(bottomRight, topRight, bottomLeft, topLeft)
        val ordered = PanelOrdering.order(shuffled, rightToLeft = true)
        assertEquals(listOf(topRight, topLeft, bottomRight, bottomLeft), ordered)
    }

    @Test
    fun slightlyMisalignedPanelsStillShareARow() {
        // Vertical ranges overlap well over half of the shorter panel's height.
        val left = Panel(0.0f, 0.10f, 0.45f, 0.45f)
        val right = Panel(0.55f, 0.05f, 1.0f, 0.40f)
        val ordered = PanelOrdering.order(listOf(right, left))
        assertEquals(listOf(left, right), ordered)
    }

    @Test
    fun barelyOverlappingPanelsFormSeparateRows() {
        // Overlap is far below half of the shorter panel's height → two rows, top first.
        val upper = Panel(0.5f, 0.0f, 1.0f, 0.32f)
        val lower = Panel(0.0f, 0.3f, 0.45f, 0.7f)
        val ordered = PanelOrdering.order(listOf(lower, upper))
        assertEquals(listOf(upper, lower), ordered)
    }

    @Test
    fun emptyAndSingleListsPassThrough() {
        assertEquals(emptyList(), PanelOrdering.order(emptyList()))
        assertEquals(listOf(topLeft), PanelOrdering.order(listOf(topLeft)))
    }
}
