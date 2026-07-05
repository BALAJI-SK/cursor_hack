import SwiftUI

/// AGAM · Chitra Katha brand palette — kept in sync with the Android theme (Color.kt).
enum AGAM {
    static let ink = Color(hex: 0x17100E)
    static let inkSoft = Color(hex: 0x2A201C)
    static let crimson = Color(hex: 0xD11F2D)
    static let crimsonBright = Color(hex: 0xE62534)
    static let maroon = Color(hex: 0x7C1620)
    static let maroonDeep = Color(hex: 0x5C0F18)
    static let cream = Color(hex: 0xF3E9D6)
    static let paper = Color(hex: 0xFAF3E4)
    static let ochre = Color(hex: 0xE0A22B)
    static let creamMuted = Color(hex: 0xF3E9D6).opacity(0.55)
}

/// Brand type: Anton (display — wordmark, titles, page numbers) and Archivo (UI labels, body).
/// The variable Archivo registers as its SemiBold instance on iOS; tracking + uppercase carry the
/// kicker/label look that Android gets from heavier weights.
extension Font {
    static func anton(_ size: CGFloat) -> Font { .custom("Anton-Regular", fixedSize: size) }
    static func archivo(_ size: CGFloat) -> Font { .custom("Archivo-SemiBold", fixedSize: size) }
}

extension Color {
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: 1
        )
    }
}

/// Archivo kicker: uppercase, wide tracking — the tag/label style used across the UI.
struct KickerText: View {
    let text: String
    var size: CGFloat = 11
    var color: Color = AGAM.creamMuted
    init(_ text: String, size: CGFloat = 11, color: Color = AGAM.creamMuted) {
        self.text = text; self.size = size; self.color = color
    }
    var body: some View {
        Text(text.uppercased())
            .font(.archivo(size))
            .tracking(2)
            .foregroundColor(color)
    }
}
