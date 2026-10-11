# GPT(이미지 생성)용 프롬프트 4종

엔진은 아래 파일이 `assets/`에 있으면 그걸 쓰고, 없으면 기존 코드 그림을 씁니다.
GPT가 만든 원본은 `raw/` 같은 곳에 두고 `tools/prep-assets.py`로 규격에 맞춰 변환하세요.

공통 규칙: **글자·로고·캐릭터·UI 요소를 넣지 말 것.** 글자는 엔진이 얹습니다.
GPT에 "no text, no letters, no logos, no watermark"를 항상 붙이세요.

---
## 1. 배경 `bg-main`  (세로 1024x1536으로 요청 → 변환 시 9:16으로 중앙 크롭)
```
Vertical background illustration for a mobile game arena, 2:3 portrait.
Deep indigo and violet night sky with a glowing magenta-cyan nebula, soft floating light
particles and distant bokeh, a faint glowing synthwave perspective grid floor in the bottom
fifth. Cinematic, polished 3D-render look, rich depth.
IMPORTANT: keep the middle 60% of the image calm and dark so game objects stand out; put the
detail and glow near the edges and corners. Keep important details away from the left and
right 10% edges. No text, no letters, no logos, no characters, no UI, no watermark.
```
변환: `python3 tools/prep-assets.py raw/bg.png bg-main`

## 2. 아레나 바닥 `arena-floor`  (정사각 1024x1024, 투명 배경 PNG)
```
Top-down orthographic view of a perfectly circular glossy dark sci-fi arena floor, centered,
the circle fills 96% of a square canvas, transparent background outside the circle.
Deep purple-black reflective glass surface, faint concentric neon rings and a subtle hex grid,
soft light reflections, slight vignette toward the edge, a thin glowing violet rim.
Calm and low-contrast in the center. No text, no characters, no logos, no watermark.
```
변환: `python3 tools/prep-assets.py raw/floor.png arena-floor`

## 3. 패널 `panel`  (가로 1536x1024로 요청, 투명 배경 PNG)
```
A single wide horizontal sci-fi game UI panel frame, centered, transparent background.
Rounded rectangle with a thin glowing violet neon border, small tasteful corner bracket
details, dark translucent glass interior that is EMPTY (no content), subtle inner glow.
Aspect about 4:1 (very wide and short). Flat front view. No text, no icons, no logos.
```
변환: `python3 tools/prep-assets.py raw/panel.png panel`
(엔진이 9분할로 늘려서 제목 패널과 순위 카드에 씁니다. 모서리 장식은 작게 부탁하세요.)
위기 구간에는 엔진이 색을 붉게 돌립니다.

## 4. 우승 광선 `rays`  (정사각 1024x1024, 투명 배경 PNG)
```
Radial burst of golden-white light rays radiating from the exact center of a square canvas,
transparent background, 16 to 24 soft tapered rays of varying length, subtle sparkles and a
soft glow near the center, rays fade out toward the edges. Victory celebration effect.
No text, no characters, no logos.
```
변환: `python3 tools/prep-assets.py raw/rays.png rays`

---
## 5. 음식 아이콘 `assets/icons/<slug>.png`  (작은 구슬 안에 들어가는 그림)
구슬 안에서는 **지름 60~70px**로 보입니다. 그래서 **단순하고, 윤곽이 굵고, 색이 선명한 한 덩어리 아이콘**이 좋습니다.
세부 묘사가 많으면 뭉개집니다. 한 장에 12개를 한꺼번에 만들면 품질이 떨어지기 쉬워서, **6개씩 두 장**을 권합니다.

### 5-A. 첫 번째 시트 (3열 x 2행 = 6개)
```
A sticker-style icon sheet: 6 cute glossy food icons arranged in a clean 3 columns x 2 rows grid,
transparent background, each icon fully separated by wide empty gaps (no touching, no overlap),
all the same size and centered in its cell. Consistent style: glossy 3D cartoon, thick soft white
outline, bold saturated colors, simple readable shapes, soft highlight, minimal detail (it will be
shown very small). Order, left to right, top to bottom:
1 fried chicken drumstick (golden crispy),
2 pizza slice with melting cheese and pepperoni,
3 tteokbokki: Korean spicy rice cakes (chewy cylinder-shaped white rice cakes) in glossy red-orange gochujang sauce with a piece of flat fish cake, in a small dish,
4 ramen noodle bowl with egg and steam,
5 gimbap: a cut slice of Korean seaweed rice roll seen from the cut side, black seaweed ring, white rice, colorful fillings (yellow pickled radish, carrot, spinach, egg, ham),
6 samgyeopsal: three thick strips of grilled pork belly with white and pink layers, slightly charred.
No text, no letters, no logos, no watermark.
```
변환: `python3 tools/slice-icons.py raw/food-a.png configs/food.json --rows 2 --start 0 --count 6`

### 5-B. 두 번째 시트 (3열 x 2행 = 6개)
```
(the same style paragraph as sheet A) Order, left to right, top to bottom:
1 sushi: a nigiri with salmon on rice,
2 hamburger with sesame bun, patty, lettuce, tomato and cheese,
3 jjajangmyeon: Korean black bean sauce noodles in a white bowl, glossy dark sauce on yellow noodles with a few cucumber strips on top,
4 malatang: a bowl of bright red spicy soup with tofu cubes, bok choy, lotus root slices and dried red chilies,
5 jokbal: three thick slices of braised pig's trotters, glossy dark brown skin edge with pale pink meat, on a lettuce leaf,
6 kimchi jjigae: red kimchi stew bubbling in a black earthenware pot with tofu and green onion.
```
변환: `python3 tools/slice-icons.py raw/food-b.png configs/food.json --rows 2 --start 6 --count 6`

슬라이서는 아이콘 사이가 **떨어져 있어야** 자를 수 있습니다. 개수가 안 맞으면 `-debug.png`를 만들어서 어디가 붙었는지 보여줍니다.
결과 `assets/icons/chicken.png` 등이 있으면 엔진이 이모지·손그림 대신 이 그림을 씁니다.
한 개만 다시 만들고 싶으면: `A single glossy 3D cartoon <음식> icon, thick soft white outline, transparent background, centered, no text` 로 요청하고,
`python3 tools/slice-icons.py raw/one.png configs/food.json --rows 1 --start <번호> --count 1`

### 5-C. (선택) 요일 아이콘 7개 `mon…sun`
```
(the same style paragraph) 7 icons in a row-friendly grid (4 columns x 2 rows, last cell empty), order:
1 crescent moon, 2 flame, 3 water drop, 4 small tree, 5 gold coin bag, 6 mountain, 7 sun.
```
변환: `python3 tools/slice-icons.py raw/week.png configs/weekday.json --rows 2`

---
## 쓰는 법
1. GPT에서 위 프롬프트로 이미지를 만들고 원본을 저장합니다.
2. 이 대화에 이미지를 첨부해 주시면 제가 `assets/`로 변환해 넣고 확인 영상을 뽑습니다.
   (또는 `studio/engine/raw/`에 올려 push하세요.)
3. 결과가 마음에 안 들면 프롬프트를 고쳐 다시 만들면 됩니다. 엔진은 그대로입니다.

## 라이선스
이미지 생성 서비스의 약관(상업적 이용 가능 여부)을 확인하세요. 이 엔진은 만들어진 이미지를 그대로 쓰기만 합니다.
