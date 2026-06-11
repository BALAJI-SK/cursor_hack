package com.chakra.comicreader.data.archive

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class NaturalOrderTest {

    @Test
    fun embeddedNumbersSortNumerically() {
        val sorted = listOf("page10.jpg", "page2.jpg", "page1.jpg")
            .sortedWith(NaturalOrderComparator)
        assertEquals(listOf("page1.jpg", "page2.jpg", "page10.jpg"), sorted)
    }

    @Test
    fun leadingZerosCompareEqualToUnpadded() {
        assertEquals(0, NaturalOrderComparator.compare("page002", "page2"))
    }

    @Test
    fun comparisonIsCaseInsensitive() {
        assertEquals(0, NaturalOrderComparator.compare("Page1", "page1"))
        assertTrue(NaturalOrderComparator.compare("Apple", "banana") < 0)
    }

    @Test
    fun prefixSortsBeforeLongerString() {
        assertTrue(NaturalOrderComparator.compare("page", "page1") < 0)
    }

    @Test
    fun mixedSegmentsSortPerSegment() {
        val sorted = listOf("ch2-page10", "ch10-page1", "ch2-page9")
            .sortedWith(NaturalOrderComparator)
        assertEquals(listOf("ch2-page9", "ch2-page10", "ch10-page1"), sorted)
    }
}

class IsImageEntryTest {

    @Test
    fun acceptsCommonImageExtensions() {
        for (name in listOf("p.jpg", "p.JPEG", "p.png", "p.webp", "p.gif", "p.bmp", "p.avif")) {
            assertTrue(isImageEntry(name), "expected $name to be an image entry")
        }
    }

    @Test
    fun rejectsNonImagesAndMetadata() {
        assertFalse(isImageEntry("info.txt"))
        assertFalse(isImageEntry("ComicInfo.xml"))
        assertFalse(isImageEntry("noextension"))
    }

    @Test
    fun rejectsHiddenAndMacOsxEntries() {
        assertFalse(isImageEntry(".hidden.jpg"))
        assertFalse(isImageEntry("__MACOSX-resource.jpg"))
        assertFalse(isImageEntry("__MACOSX/._page1.jpg"))
    }

    @Test
    fun usesLeafNameForNestedEntries() {
        assertTrue(isImageEntry("vol1/ch2/page3.png"))
        assertTrue(isImageEntry("vol1\\ch2\\page3.png"))
        assertFalse(isImageEntry("vol1/.thumbs/.cover.png"))
    }
}
