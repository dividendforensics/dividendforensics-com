#!/usr/bin/env python3
"""
DFB 사이트 빌더.

articles.json 하나를 읽어서 아래 세 파일의 생성 구간만 다시 씁니다.

  index.html         ARTICLES:START ~ ARTICLES:END  (대표 1건 + 목록, home:false 제외)
  research.html      ARTICLES:START ~ ARTICLES:END  (group 별 묶음)
  index.html / research-desk.html
                     <b data-dfb="count">NN</b>      (발행 건수)

설계 원칙
  - 마커 밖은 절대 건드리지 않는다.
  - 배열 순서가 곧 표시 순서다. 정렬하지 않는다.
  - 검증에 실패하면 아무것도 쓰지 않고 0이 아닌 코드로 죽는다.
    (잘못된 JSON 한 번으로 목록이 통째로 날아가는 것을 막기 위함)

사용:  python build_site.py [--check]
       --check 를 주면 쓰지 않고 변경 필요 여부만 알려준다 (CI 용).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "articles.json"

START = "<!-- ARTICLES:START -->"
END = "<!-- ARTICLES:END -->"
COUNT_RE = re.compile(r'(<b\s+data-dfb="count">)(\d+)(</b>)')


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- 이스케이프

def esc(s: str) -> str:
    """평문을 사이트 표기에 맞는 HTML 엔티티로. & 를 가장 먼저 처리해야 한다."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (s.replace("’", "&rsquo;").replace("‘", "&lsquo;")
             .replace("“", "&ldquo;").replace("”", "&rdquo;")
             .replace("—", "&mdash;").replace("–", "&ndash;")
             .replace("−", "&minus;"))


# ---------------------------------------------------------------- 검증

REQUIRED = ("url", "title", "blurb", "date", "group", "label")


def load():
    if not DATA.exists():
        raise BuildError(f"{DATA} 가 없습니다.")
    try:
        cfg = json.loads(DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"articles.json 문법 오류 — {e.lineno}행 {e.colno}칸: {e.msg}")

    if not isinstance(cfg, dict):
        raise BuildError("articles.json 최상위 값은 객체여야 합니다. articles 배열과 published_count 를 확인하세요.")

    arts = cfg.get("articles")
    if not isinstance(arts, list) or not arts:
        raise BuildError("articles 가 비어 있거나 배열이 아닙니다. 목록을 통째로 지울 수는 없습니다.")

    seen = set()
    for i, a in enumerate(arts, 1):
        if not isinstance(a, dict):
            raise BuildError(f"{i}번째 항목이 객체가 아닙니다.")
        for f in REQUIRED:
            if not str(a.get(f, "")).strip():
                raise BuildError(f"{i}번째 항목에 '{f}' 가 없거나 비어 있습니다. (url={a.get('url','?')})")
        if not str(a["url"]).startswith("https://"):
            raise BuildError(f"{i}번째 항목의 url 이 https:// 로 시작하지 않습니다: {a['url']}")
        if a["url"] in seen:
            raise BuildError(f"url 이 중복입니다: {a['url']}")
        seen.add(a["url"])

    cnt = cfg.get("published_count")
    if not isinstance(cnt, int) or cnt < 1:
        raise BuildError("published_count 는 1 이상의 정수여야 합니다.")
    if cnt < len(arts):
        raise BuildError(f"published_count({cnt}) 가 목록 길이({len(arts)})보다 작습니다.")

    return cfg, arts, cnt


# ---------------------------------------------------------------- 생성

def row(a, *, home):
    title = a.get("home_title") if home and a.get("home_title") else a["title"]
    label = a.get("home_label") if home and a.get("home_label") else a["label"]
    meta = f'{esc(a["date"])} &middot; {esc(label)}'
    if not home:
        meta += " &middot; Read on Benzinga &rarr;"
    return (
        f'    <a class="row" href="{a["url"]}" target="_blank" rel="noopener">\n'
        f'      <span class="rt">{esc(title)}</span>\n'
        f'      <span class="rd">{esc(a["blurb"])}</span>\n'
        f'      <span class="rmeta">{meta}</span>\n'
        f'    </a>\n'
    )


def build_index(arts):
    home_arts = [a for a in arts if a.get("home", True) is not False]
    if not home_arts:
        raise BuildError("첫 페이지에 표시할 기사가 없습니다. 모든 항목이 home:false 입니다.")

    lead, rest = home_arts[0], home_arts[1:]
    lead_title = lead.get("home_title") or lead["title"]
    lead_label = lead.get("home_label") or lead["label"]
    lead_html = (
        f'  <a class="home-case-lead" href="{lead["url"]}" target="_blank" rel="noopener">\n'
        f'    <span class="home-case-index">Featured case file</span>\n'
        f'    <span class="home-case-title">{esc(lead_title)}</span>\n'
        f'    <span class="home-case-blurb">{esc(lead["blurb"])}</span>\n'
        f'    <span class="home-case-meta">{esc(lead["date"])} &middot; {esc(lead_label)} &middot; Read on Benzinga &rarr;</span>\n'
        f'  </a>\n'
    )
    rows = "".join(row(a, home=True) for a in rest)
    rows_html = f'  <div class="rows home-case-list">\n{rows}  </div>\n' if rows else ""
    return f'\n<div class="home-cases">\n{lead_html}{rows_html}</div>\n  '


def build_research(arts):
    order, groups = [], {}
    for a in arts:                      # 그룹 순서 = 배열에서 처음 나온 순서
        g = a["group"]
        if g not in groups:
            order.append(g)
            groups[g] = []
        groups[g].append(a)

    blocks = []
    for g in order:
        rows = "".join(row(a, home=False) for a in groups[g])
        blocks.append(
            f'  <div class="grp"><div class="grp-h">{esc(g)}</div>\n'
            f'  <div class="rows">\n{rows}  </div></div>\n'
        )
    return "\n" + "\n".join(blocks) + "\n\n  "


def splice(path: Path, inner: str) -> str:
    text = path.read_text(encoding="utf-8")
    i, j = text.find(START), text.find(END)
    if i == -1 or j == -1:
        raise BuildError(f"{path.name} 에 ARTICLES 마커가 없습니다. 마커를 지우지 마세요.")
    if j < i:
        raise BuildError(f"{path.name} 의 마커 순서가 뒤바뀌었습니다.")
    return text[: i + len(START)] + inner + text[j:]


def stamp_count(path: Path, n: int) -> str:
    text = path.read_text(encoding="utf-8")
    if not COUNT_RE.search(text):
        raise BuildError(
            f'{path.name} 에 <b data-dfb="count"> 표식이 없습니다. '
            "히어로 발행 건수 <b> 태그에 data-dfb=\"count\" 를 남겨두세요."
        )
    return COUNT_RE.sub(lambda m: m.group(1) + str(n) + m.group(3), text)


# ---------------------------------------------------------------- 진입점

def main():
    check = "--check" in sys.argv
    try:
        cfg, arts, cnt = load()
        index = splice(ROOT / "index.html", build_index(arts))
        if not COUNT_RE.search(index):
            raise BuildError(
                'index.html 에 <b data-dfb="count"> 표식이 없습니다. '
                '발행 건수 표식을 남겨두세요.'
            )
        index = COUNT_RE.sub(lambda m: m.group(1) + str(cnt) + m.group(3), index)
        planned = {
            ROOT / "index.html":         index,
            ROOT / "research.html":      splice(ROOT / "research.html", build_research(arts)),
            ROOT / "research-desk.html": stamp_count(ROOT / "research-desk.html", cnt),
        }
    except BuildError as e:
        print(f"빌드 중단: {e}", file=sys.stderr)
        print("아무 파일도 수정하지 않았습니다.", file=sys.stderr)
        return 1

    changed = []
    for path, new in planned.items():
        if path.read_text(encoding="utf-8") != new:
            changed.append(path.name)
            if not check:
                path.write_text(new, encoding="utf-8")

    home = sum(1 for a in arts if a.get("home", True) is not False)
    print(f"기사 {len(arts)}건 (첫 페이지 {home}건) · 발행 건수 {cnt}")
    if not changed:
        print("변경 없음.")
    elif check:
        print("갱신 필요:", ", ".join(changed))
        return 1
    else:
        print("갱신함:", ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
