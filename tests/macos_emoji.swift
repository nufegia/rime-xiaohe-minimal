// SPDX-License-Identifier: GPL-3.0-or-later
// Reproduce Squirrel 1.1.2's candidate attribute boundaries, not just font coverage.
import AppKit
import CoreText

let emojiFont = NSFont(name: "AppleColorEmoji", size: 16)!
let base = NSFont.systemFont(ofSize: 16)
let font = NSFont(descriptor: base.fontDescriptor.addingAttributes([
    .cascadeList: [emojiFont.fontDescriptor]
]), size: 16)!
let noBreak = NSAttributedString.Key("noBreak")

func formatCandidate(_ candidate: String, format: String) -> NSAttributedString {
    let line = NSMutableAttributedString(string: format, attributes: [.font: font])
    let marker = (line.string as NSString).range(of: "[candidate]")
    // SquirrelPanel.update applies noBreak from the marker's second UTF-16 unit.
    if candidate.count <= 5 {
        line.addAttribute(noBreak, value: true,
                          range: NSRange(location: marker.location + 1, length: marker.length - 1))
    }
    line.mutableString.replaceOccurrences(of: "[candidate]", with: candidate,
                                         range: NSRange(location: 0, length: line.length))
    if line.length <= 10 {
        line.addAttribute(noBreak, value: true,
                          range: NSRange(location: 1, length: line.length - 1))
    }
    return line
}

func hasBrokenGlyphs(_ text: NSAttributedString) -> Bool {
    let line = CTLineCreateWithAttributedString(text)
    for run in CTLineGetGlyphRuns(line) as! [CTRun] {
        let attributes = CTRunGetAttributes(run) as NSDictionary
        let actual = attributes[kCTFontAttributeName] as! CTFont
        if (CTFontCopyPostScriptName(actual) as String) == "LastResort" { return true }
        var glyphs = [CGGlyph](repeating: 0, count: CTRunGetGlyphCount(run))
        CTRunGetGlyphs(run, CFRange(location: 0, length: 0), &glyphs)
        if glyphs.contains(0) { return true }
    }
    return false
}

let configuredFormat = CommandLine.arguments[1]
// Control case must reproduce the reported symptom, otherwise this is not a useful test.
precondition(!hasBrokenGlyphs(formatCandidate("❓", format: "[candidate]")))
precondition(hasBrokenGlyphs(formatCandidate("🔴", format: "[candidate]")))
for candidate in ["❓", "🔴", "🟡", "🟢", "🔵", "❤️", "👍🏽", "🇨🇳"] {
    precondition(!hasBrokenGlyphs(formatCandidate(candidate, format: configuredFormat)),
                 "Broken candidate rendering: \(candidate)")
}
print("Candidate attribute-boundary regression passed: BMP control, broken bare non-BMP control, configured emoji rendering.")
