import UIKit

/// Loads and caches comic cover thumbnails (page 0 of each CBZ), decoded small for the grid.
enum CoverLoader {
    private static let cache = NSCache<NSURL, UIImage>()

    static func cover(for url: URL) async -> UIImage? {
        if let cached = cache.object(forKey: url as NSURL) { return cached }
        let image: UIImage? = await Task.detached(priority: .userInitiated) {
            guard let archive = try? CbzArchive(url: url), archive.pageCount > 0,
                  let data = try? archive.readPage(0), let full = UIImage(data: data) else {
                return nil
            }
            return await full.byPreparingThumbnail(ofSize: CGSize(width: 400, height: 600)) ?? full
        }.value
        if let image { cache.setObject(image, forKey: url as NSURL) }
        return image
    }
}
