import UIKit
import AGAMShared

/// Refines ML-detected panel boxes by splitting any box that still contains a clear interior
/// "gutter" — the blank channel between bordered comic panels — recovering panels the detector
/// merged into one box. It cannot help truly borderless art (no gutter to find); that's a model
/// limitation.
///
/// Algorithm (after Pang/Cao/Lau/Chan, "A Robust Panel Extraction Method for Manga", ACM MM 2014):
///  - **Adaptive threshold (Otsu):** "blank" is decided per page from the grayscale histogram, not a
///    fixed near-white constant — so cream paper / colored gutters on Western comics still register.
///  - **Confidence-scored cut lines:** each candidate line scores `blank_pixels / line_length` ∈ [0,1];
///    a line crossing the whole region without hitting content scores ~1.0. We pick the single
///    highest-confidence line and choose horizontal vs. vertical adaptively (whichever scores higher),
///    cutting only when confidence clears a threshold. Recurses on the two halves.
///
/// iOS-only for now (Android is intentionally left as-is); the math is pure arithmetic on the gray
/// buffer, so it can move into shared Kotlin later if parity is ever wanted.
struct GutterRefiner {
    private let gray: [UInt8]   // row-major, gw*gh, 0 = black … 255 = white
    private let gw: Int
    private let gh: Int
    private let blankLevel: Int // Otsu threshold: pixels ≥ this are "blank" (gutter/background)

    // A line must be at least this blank to count as a gutter; gutters away from box edges only.
    private let confidence: Double = 0.92
    private let edgeMargin: Double = 0.06
    private let minPanelFrac: Float = 0.05
    private let maxDepth = 4

    /// Builds the refiner from a page image, downsampling to ~900px long edge for speed.
    init?(image: UIImage) {
        guard let cg = image.cgImage else { return nil }
        let longEdge = max(cg.width, cg.height)
        let scale = longEdge > 900 ? 900.0 / Double(longEdge) : 1.0
        let w = max(1, Int(Double(cg.width) * scale))
        let h = max(1, Int(Double(cg.height) * scale))
        var buf = [UInt8](repeating: 0, count: w * h)
        let ok: Bool = buf.withUnsafeMutableBytes { raw in
            guard let ctx = CGContext(
                data: raw.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w,
                space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue
            ) else { return false }
            ctx.interpolationQuality = .low
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
            return true
        }
        guard ok else { return nil }
        gray = buf; gw = w; gh = h
        blankLevel = GutterRefiner.otsuThreshold(buf)
    }

    /// Splits each panel along interior gutters, returning the refined set (unordered).
    func refine(_ panels: [Panel]) -> [Panel] {
        panels.flatMap { split($0, depth: maxDepth) }
    }

    private func split(_ p: Panel, depth: Int) -> [Panel] {
        if depth <= 0 { return [p] }
        let x0 = clamp(Int(Double(p.left) * Double(gw)), 0, gw - 1)
        let x1 = clamp(Int(Double(p.right) * Double(gw)), x0 + 1, gw)
        let y0 = clamp(Int(Double(p.top) * Double(gh)), 0, gh - 1)
        let y1 = clamp(Int(Double(p.bottom) * Double(gh)), y0 + 1, gh)
        if (x1 - x0) < 8 || (y1 - y0) < 8 { return [p] }

        let vCut = bestCut(vertical: true, x0: x0, x1: x1, y0: y0, y1: y1)
        let hCut = bestCut(vertical: false, x0: x0, x1: x1, y0: y0, y1: y1)

        // Adaptive: take whichever axis has the cleaner gutter (highest confidence).
        if let v = vCut, (hCut == nil || v.confidence >= hCut!.confidence) {
            let cutN = Float(v.center) / Float(gw)
            if cutN - p.left >= minPanelFrac, p.right - cutN >= minPanelFrac {
                let left = Panel(left: p.left, top: p.top, right: cutN, bottom: p.bottom)
                let right = Panel(left: cutN, top: p.top, right: p.right, bottom: p.bottom)
                return split(left, depth: depth - 1) + split(right, depth: depth - 1)
            }
        }
        if let h = hCut {
            let cutN = Float(h.center) / Float(gh)
            if cutN - p.top >= minPanelFrac, p.bottom - cutN >= minPanelFrac {
                let top = Panel(left: p.left, top: p.top, right: p.right, bottom: cutN)
                let bot = Panel(left: p.left, top: cutN, right: p.right, bottom: p.bottom)
                return split(top, depth: depth - 1) + split(bot, depth: depth - 1)
            }
        }
        return [p]
    }

    /// Highest-confidence blank line within the box's central band along one axis. Confidence is the
    /// fraction of the line that is blank (≥ Otsu level); we return the center of the contiguous
    /// high-confidence band (so the cut sits in the middle of the gutter), or nil if none clears the bar.
    private func bestCut(vertical: Bool, x0: Int, x1: Int, y0: Int, y1: Int) -> (center: Int, confidence: Double)? {
        let lineCount = vertical ? (x1 - x0) : (y1 - y0)
        let span = vertical ? (y1 - y0) : (x1 - x0)
        if lineCount < 12 || span < 8 { return nil }
        let lo = Int(Double(lineCount) * edgeMargin)
        let hi = lineCount - lo
        if hi - lo < 1 { return nil }

        // Per-line blank fraction across the candidate band.
        var conf = [Double](repeating: 0, count: lineCount)
        var bestIdx = -1
        var bestConf = 0.0
        var i = lo
        while i < hi {
            let c = blankFraction(vertical: vertical, index: (vertical ? x0 : y0) + i,
                                  start: vertical ? y0 : x0, end: vertical ? y1 : x1)
            conf[i] = c
            if c > bestConf { bestConf = c; bestIdx = i }
            i += 1
        }
        if bestIdx < 0 || bestConf < confidence { return nil }

        // Expand to the contiguous band of confident lines around the peak; cut at its center.
        var a = bestIdx, b = bestIdx
        while a > lo && conf[a - 1] >= confidence { a -= 1 }
        while b < hi - 1 && conf[b + 1] >= confidence { b += 1 }
        let center = (vertical ? x0 : y0) + (a + b) / 2
        return (center, bestConf)
    }

    /// Fraction of a single column (vertical) or row of the box that is blank (≥ Otsu threshold).
    private func blankFraction(vertical: Bool, index: Int, start: Int, end: Int) -> Double {
        var blank = 0, total = 0
        if vertical {
            var y = start
            while y < end { if Int(gray[y * gw + index]) >= blankLevel { blank += 1 }; total += 1; y += 1 }
        } else {
            var x = start
            while x < end { if Int(gray[index * gw + x]) >= blankLevel { blank += 1 }; total += 1; x += 1 }
        }
        return total == 0 ? 0 : Double(blank) / Double(total)
    }

    /// Otsu's method: the grayscale level that best separates dark content from light background.
    /// Pixels at or above it are treated as "blank" (gutter/paper), adapting per page to cream paper
    /// or lightly-colored gutters instead of assuming pure white.
    private static func otsuThreshold(_ gray: [UInt8]) -> Int {
        var hist = [Int](repeating: 0, count: 256)
        for v in gray { hist[Int(v)] += 1 }
        let total = gray.count
        if total == 0 { return 200 }
        var sumAll = 0.0
        for t in 0..<256 { sumAll += Double(t * hist[t]) }
        var sumB = 0.0, wB = 0, best = -1.0, thr = 200
        for t in 0..<256 {
            wB += hist[t]
            if wB == 0 { continue }
            let wF = total - wB
            if wF == 0 { break }
            sumB += Double(t * hist[t])
            let mB = sumB / Double(wB)
            let mF = (sumAll - sumB) / Double(wF)
            let between = Double(wB) * Double(wF) * (mB - mF) * (mB - mF)
            if between > best { best = between; thr = t }
        }
        // Bias slightly toward the light side so faint content near the gutter still reads as content.
        return min(254, thr + 1)
    }

    private func clamp(_ v: Int, _ lo: Int, _ hi: Int) -> Int { min(max(v, lo), hi) }
}
