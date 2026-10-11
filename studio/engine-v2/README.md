# Engine v2 — record-then-replay, miniature-tray look (comparison working copy)

The original engine is kept untouched in `studio/engine` (commit `7a674c3`, physics `p5`).
This folder is a working copy for the visual-quality brief. Don't render full episodes from here
until the comparison drafts have been reviewed.

## Structure
| File | Role |
|---|---|
| `sim.mjs` | Pure simulation. It runs the whole match before frame 0 and records positions (every 1/120 s) plus every collision, hit and elimination as events. No rendering, no clock. |
| `replay.mjs` | Presentation layer. Maps video time to simulation time (slow-motion) and walks the event record. It only reads the record. |
| `scene.html` | New look. `?look=v3d` is real 3D glass spheres; `?look=v25` paints the beads in 2D. The tray, camera, light, shadows and HUD are shared. |
| `legacy.html` | The p5 visuals as-is, driven by the same record (for comparison). |
| `scenarios.mjs` | Comparison scenes: `still3`, `clash`, `crowd12` (same foods and placement in every look). |
| `cmp.sh`, `tools/compose-cmp.py` | Comparison renders and side-by-side composites. |
| `sim-check.mjs`, `verify.cjs` | Outcome checks (see below). |

## Why the result is fixed
Every input that decides the result is pinned and written into `PHYS_VER`:
- initial state
- rule version
- rng call order
- physics time step: 1/120 s fixed; slow-motion does not change it
- arithmetic: only `+ - * /` and `sqrt`

Change log of the s13 winner:

| Version | s13 winner | Cause |
|---|---|---|
| Early | 짜장면 | Physics step dt = 1/30 × slow-mo factor. Slow-mo (presentation) changed the integration. |
| Next renders | 김밥 | Changing the slow-mo policy changed dt. Ball size was also tuned. Unintended. |
| p5 | 피자 | Fixed 120 Hz step (decoupled from slow-mo) plus a deliberate start-radius change. |
| p5 (found now) | — | Same code, node 22 gives 떡볶이 and Chromium 141 gives 피자. `Math.sin`/`Math.cos` differ in the last bits between JS engines, so results also depended on browser version. |
| **p6** | 짜장면 | Physics uses only `+ - * / sqrt` (custom sin/cos/atan2). Start slots are now shuffled per seed (deliberate, for fairness). |

- **p6 verification:**
  - node and Chromium produce identical winners and full elimination orders for 60 seeds.
  - Over 2000 seeds the winner counts are even across entries: 12 entries χ²=6.9 (df 11), 16 entries χ²=16.3 (df 15).
  - Before the change, start slot 8 had 29/600 wins vs about 50 expected.
- **Presentation independence:** `node verify.cjs configs/food.json 13,22,...`. It plays the same seed under legacy, v25 with slow-mo, v25 without slow-mo, and v3d, and compares against the node simulation.

## Commands
```
node sim-check.mjs configs/food.json 13,22          # winner + elimination order (no browser, ~0.1 s)
node verify.cjs configs/food.json 13,22             # same result under every look / slow-mo setting
./cmp.sh                                             # still3 / clash / crowd12 × legacy / v25 / v3d
python3 tools/compose-cmp.py out food-s13 clash      # side-by-side composite
node render.js configs/food.json --seeds 13 --look v3d    # full episode (after a look is chosen)
```
