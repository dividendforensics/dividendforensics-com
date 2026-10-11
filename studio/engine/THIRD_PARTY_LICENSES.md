# Third-party licenses used by the engine

What the rendered videos and the engine actually use. Anything else is not used and is not in `package.json`.

| Component | Used for | License | Notice / source |
|---|---|---|---|
| Black Han Sans | Hangul display text | SIL OFL 1.1 | "Copyright 2015 The Black Han Sans Authors" (`node_modules/@fontsource/black-han-sans/LICENSE`) |
| Bungee | digits and Latin (ranks, timers, GO!) | SIL OFL 1.1 | "Copyright 2023 The Bungee Project Authors (https://github.com/djrrb/Bungee)" (`node_modules/@fontsource/bungee/LICENSE`) |
| Pretendard | small UI text (record times) | SIL OFL 1.1 | `node_modules/pretendard/package.json` declares OFL-1.1; the README states commercial use is allowed except selling the font by itself. **The copyright line itself was not found in the npm package; copy it from the project's official LICENSE before redistributing the font files.** |
| Noto Color Emoji | emoji glyphs drawn from the system font | SIL OFL 1.1 (font) / Apache-2.0 (tooling), per the Debian package copyright file | `/usr/share/doc/fonts-noto-color-emoji/copyright` |
| three.js | 3D rendering | MIT | https://github.com/mrdoob/three.js |
| Art images (background, arena floor, panel, rays, food/weekday icons) | visuals | Generated with an image model | Terms of the generating service apply; check them for commercial use before publishing. |

## Rules for redistributing font files
OFL fonts may be used and bundled commercially, but the license text and copyright notice must travel with the font files,
and the fonts may not be sold on their own. Rendered videos only embed glyph shapes and need no extra notice.
Keep the `LICENSE` files in `node_modules/@fontsource/*` if you ship the engine folder with its fonts.

## Verification status (honest)
- Black Han Sans and Bungee: license text read from the package files (OFL 1.1).
- Pretendard: OFL declared in package metadata; copyright line not verified from the original file.
- 32 other fonts were installed only to compare looks (their package license files named OFL, one named Apache-2.0);
  they were not checked against the original foundry pages and were **removed** from the project after the comparison.
