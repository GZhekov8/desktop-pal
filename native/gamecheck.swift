// Desktop Pal game check for macOS: tells the app whether a full-screen GAME is in front.
// Prints one line whenever the answer changes (and every 60 s):  <state>|<fullscreen 0/1>|<app name>|<app category>
//   state 3 = a game is full screen in front, 2 = some other app is full screen, 5 = nothing full screen.
// Many Mac users run normal apps full screen, so only games count: apps whose Info.plist category is a
// games category, or that live in a game store folder (Steam, Epic, GOG, Battle.net, CrossOver...).
// Needs no special permissions (window sizes and owners are public; titles aren't read).
// Exits when the app closes its stdin.
// Build (universal): swiftc -O -target arm64-apple-macos11 gamecheck.swift -o gc-arm64
//                    swiftc -O -target x86_64-apple-macos11 gamecheck.swift -o gc-x64
//                    lipo -create gc-arm64 gc-x64 -output gamecheck-mac
import AppKit
import Foundation

setvbuf(stdout, nil, _IOLBF, 0)
signal(SIGPIPE, SIG_IGN)

Thread.detachNewThread {
    while true {
        let d = FileHandle.standardInput.availableData
        if d.isEmpty { exit(0) }
    }
}

let storeFolders = ["steamapps", "/epic games/", "/gog games/", "/gog galaxy/games/", "battle.net", "/riot games/",
                    "/crossover/", "/whisky/", "/heroic/", "/applications/games/"]

func gameInfo(_ app: NSRunningApplication) -> (Bool, String) {
    var category = ""
    guard let url = app.bundleURL else { return (false, category) }
    if let b = Bundle(url: url) {
        category = (b.object(forInfoDictionaryKey: "LSApplicationCategoryType") as? String) ?? ""
    }
    let p = url.path.lowercased()
    if storeFolders.contains(where: { p.contains($0) }) { return (true, category) }
    return (category.lowercased().contains("games"), category)
}

// The front-most normal window (layer 0) and whether it covers a whole screen.
func frontWindow() -> (pid_t, Bool)? {
    guard let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else { return nil }
    let screens = NSScreen.screens.map { $0.frame.size }
    for w in list {
        guard let layer = w[kCGWindowLayer as String] as? Int, layer == 0,
              let pid = w[kCGWindowOwnerPID as String] as? Int32,
              let bd = w[kCGWindowBounds as String] as? NSDictionary,
              let r = CGRect(dictionaryRepresentation: bd),
              r.width >= 100, r.height >= 100 else { continue }
        let full = screens.contains { r.width >= $0.width - 1 && r.height >= $0.height - 1 }
        return (pid, full)
    }
    return nil
}

var last = ""
var lastTime = Date.distantPast
while true {
    autoreleasepool {
        var state = 5, full = 0, name = "", category = ""
        if let (pid, isFull) = frontWindow(), let app = NSRunningApplication(processIdentifier: pid) {
            name = app.executableURL?.lastPathComponent ?? app.localizedName ?? ""
            if isFull {
                full = 1
                let (game, cat) = gameInfo(app)
                category = cat
                state = game ? 3 : 2
            }
        }
        let line = "\(state)|\(full)|\(name)|\(category)"
        if line != last || Date().timeIntervalSince(lastTime) > 60 {
            print(line)
            last = line
            lastTime = Date()
        }
    }
    RunLoop.current.run(until: Date().addingTimeInterval(2))
}
