# ASCENT

A 30-second film of one air bubble rising from the seafloor to the evening sun, built
with Three.js r186 and rendered in real time. It also comes as a 12-second Lottie piece.

| File | What it is |
|---|---|
| `index.html`, `ascent.js` | The live film (open through any static server). Every frame is a function of time `t`. |
| `audio/ascent-score.m4a` | Score and sound design, synthesised by `tools/score.py` |
| `video/ascent-30s-1080p.mp4` | 1920×1080, 30 fps, H.264 + AAC, rendered with `tools/render.mjs` |
| `lottie/ascent.json` | Lottie edition, 1080×1080, 30 fps, 12 s, pure vector (no fonts or images) |
| `lottie/index.html` | Lottie preview (lottie-web, SVG or Canvas) |
| `video/ascent-lottie-1080.mp4` | The Lottie edition rendered to video with its own score |

## What is physically modelled

- **Total internal reflection.** Light passes from water (n = 1.333) into the air inside the bubble, so past ~48.6° the surface reflects completely. That gives every bubble its silver rim.
- **Diverging lens.** The air pocket shows a shrunken view of the world behind it.
- **Snell's window.** Looking up, the sky is squeezed into a 97° cone; the low sun sits near its edge.
- **Depth.** Red is absorbed first, so the reef turns blue-green with depth. The bubble grows as the pressure falls.
- **Surfacing.** The bubble becomes a thin-film dome with interference colours, then pops and leaves capillary rings.

## Shots

| t (s) | Shot |
|---|---|
| 0.0–4.9 | The reef, wide |
| 4.9–9.7 | Macro: the bubble forms in a crack and lets go (8.3) |
| 9.7–13.9 | Tracking through the kelp |
| 13.9–18.3 | Low angle into the light, a school passes overhead |
| 18.3–22.7 | Orbit around the oblate, wobbling bubble |
| 22.7–25.4 | Looking down from just below the surface |
| 25.4–26.85 | The silver underside of the surface, breaking through |
| 26.85–30.0 | Open air at dusk: the dome pops (27.75), title |

## Rendering

```sh
npm i three@0.186.1 @fontsource/cormorant-garamond @fontsource/jost
node tools/render.mjs --out frames --three node_modules/three --fonts node_modules/@fontsource
python3 tools/score.py score.wav && ffmpeg -i score.wav -c:a aac -b:a 192k audio/ascent-score.m4a
ffmpeg -framerate 30 -i frames/f_%05d.png -i audio/ascent-score.m4a -c:v libx264 -crf 19 -pix_fmt yuv420p -c:a copy ascent.mp4

python3 tools/make_lottie.py lottie/ascent.json
node tools/render_lottie.mjs node_modules lframes
```

The Lottie file was checked frame by frame in three renderers (lottie-web SVG, lottie-web
Canvas, dotLottie/ThorVG) and they match.

The follow-up series, *PIP, BELOW*, lives in `../pip-below/`.
