import UIKit
import ImageIO

/// Loads and caches comic cover thumbnails (page 0 of each CBZ). Uses ImageIO downsampling, which
/// decodes JPEG/PNG/HEIC/WebP robustly and builds a small thumbnail without inflating the full-res
/// page into memory — more reliable than UIImage(data:) + byPreparingThumbnail for big scans.
enum CoverLoader {
    private static let cache = NSCache<NSURL, UIImage>()

    static func cover(for url: URL) async -> UIImage? {
        if let cached = cache.object(forKey: url as NSURL) { return cached }
        let image: UIImage? = await Task.detached(priority: .userInitiated) {
            guard let archive = try? CbzArchive(url: url), archive.pageCount > 0,
                  let data = try? archive.readPage(0) else { return nil }
            return thumbnail(from: data, maxPixel: 600) ?? UIImage(data: data)
        }.value
        if let image { cache.setObject(image, forKey: url as NSURL) }
        return image
    }

    /// One-line diagnosis of why a cover failed: page count, page-0 byte size, the file's
    /// magic-number header, and whether the image decoders accept it.
    static func debugInfo(for url: URL) async -> String {
        await Task.detached(priority: .utility) {
            guard let archive = try? CbzArchive(url: url) else { return "open failed" }
            let n = archive.pageCount
            guard n > 0 else { return "0 pages" }
            guard let data = try? archive.readPage(0) else { return "\(n)p · read0 FAILED" }
            let magic = data.prefix(4).map { String(format: "%02X", $0) }.joined()
            let imageIO = CGImageSourceCreateWithData(data as CFData, nil) != nil
            let uiImage = UIImage(data: data) != nil
            return "\(n)p · pg0 \(data.count)B\n\(magic)\nIIO:\(imageIO) UI:\(uiImage)"
        }.value
    }

    private static func thumbnail(from data: Data, maxPixel: Int) -> UIImage? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixel,
        ]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
            return nil
        }
        return UIImage(cgImage: cg)
    }
}
