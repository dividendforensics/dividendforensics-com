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
## 쓰는 법
1. GPT에서 위 프롬프트로 이미지를 만들고 원본을 저장합니다.
2. 이 대화에 이미지를 첨부해 주시면 제가 `assets/`로 변환해 넣고 확인 영상을 뽑습니다.
   (또는 `studio/engine/raw/`에 올려 push하세요.)
3. 결과가 마음에 안 들면 프롬프트를 고쳐 다시 만들면 됩니다. 엔진은 그대로입니다.

## 라이선스
이미지 생성 서비스의 약관(상업적 이용 가능 여부)을 확인하세요. 이 엔진은 만들어진 이미지를 그대로 쓰기만 합니다.
