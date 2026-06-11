package com.chakra.comicreader.data.page

/**
 * Single source of truth for page decoding/caching, shared by Android and iOS so both platforms
 * downsample to the same dimensions and size their page cache with the same formula. Only the
 * available-memory *source* differs per platform (JVM heap on Android, physical RAM on iOS) — that
 * is unavoidable; the divisor and cap live here so the budgeting logic itself can't drift.
 */
object PageConstants {
    /** Long-edge pixel limit for a decoded page; larger scans are downsampled to this. */
    val maxPageDimension: Int = 2560

    /** Spend 1/[cacheMemoryDivisor] of available memory on the page cache. */
    val cacheMemoryDivisor: Int = 4

    /** Hard upper bound on the page cache, in bytes (512 MB). */
    val cacheMaxBytes: Int = 512 * 1024 * 1024
}
