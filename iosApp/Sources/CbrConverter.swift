import Foundation
import ZIPFoundation
import ChikaShared

/// Converts an imported CBR/RAR archive to CBZ once, on import, so the reader only ever handles
/// plain ZIP. Reading uses libarchive's BSD-licensed RAR5 reader (CbrReader); image filtering and
/// page ordering reuse the shared Kotlin core, identical to the CBZ path.
enum CbrConverter {
    enum ConversionError: LocalizedError {
        case noImages
        var errorDescription: String? {
            switch self {
            case .noImages: return "No image pages found in this archive"
            }
        }
    }

    static func convertToCbz(source: URL, destination: URL) async throws {
        try await Task.detached(priority: .userInitiated) {
            let entries = try CbrReader.readEntries(at: source)
                .filter { ComicArchiveKt.isImageEntry(name: $0.path) }
                .sorted { NaturalOrderComparator.shared.compare(a: $0.path, b: $1.path) < 0 }
            guard !entries.isEmpty else { throw ConversionError.noImages }

            // Stage images in a temp dir with zero-padded, order-preserving names, then zip into the
            // destination CBZ.
            let fm = FileManager.default
            let staging = fm.temporaryDirectory.appendingPathComponent("cbr-\(UUID().uuidString)", isDirectory: true)
            try fm.createDirectory(at: staging, withIntermediateDirectories: true)
            defer { try? fm.removeItem(at: staging) }

            for (index, item) in entries.enumerated() {
                let ext = (item.path as NSString).pathExtension
                let name = String(format: "%05d.%@", index, ext.isEmpty ? "jpg" : ext)
                try Data(item.bytes).write(to: staging.appendingPathComponent(name))
            }

            try? fm.removeItem(at: destination)
            try fm.zipItem(at: staging, to: destination, shouldKeepParent: false)
        }.value
    }
}
