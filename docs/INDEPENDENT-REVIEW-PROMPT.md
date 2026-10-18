# 다른 AI 전달용 — DFB 홈페이지 완성본 독립 검토 요청

검토 기준일: 2026-10-18 (한국 시간).
코드 배포 버전: `f3af0fb0a836e38986dd8daf984f881ef4043c42`.
배포·공개 응답 대조 상태: `PR #4 병합, CI 통과. 공개 HTML87개와 주요 자산·사이트맵·기존 이동 URL 총97응답이 로컬 배포 원본과 일치. 실제 Google 색인/광고/메일 수신은 미확인.`.

아래 요청문은 대화 내용 없이도 검토할 수 있도록 작성했다. 그대로 전달하고, 가능하면 웹·GitHub 접근이 가능한 AI에 맡긴다. 범위를 나누려면 맨 아래 추가 초점 중 하나를 덧붙인다.

---

DFB(Dividend Forensics Bureau)의 실제 홈페이지 완성본을 독립적으로 검토해 주세요. 아래 구현 설명은 검토 대상의 설명이지, 검증을 대신하는 증거가 아닙니다. 공개 사이트·고정된 코드 버전·실제 동작을 가능한 범위에서 직접 확인하고, 문제점을 구체적으로 피드백해 주세요. 답변은 한국어로 부탁드립니다.

## 1. 사이트의 목적과 실제로 만든 것

공개 사이트: https://dividendforensics.com/
저장소: https://github.com/dividendforensics/dividendforensics-com
이번 변경 PR: https://github.com/dividendforensics/dividendforensics-com/pull/4
고정 코드 버전: `f3af0fb0a836e38986dd8daf984f881ef4043c42` — main이 이후 바뀌면 이 버전과 현행 사이트를 구분해 주세요.
확장 검수 기록: https://github.com/dividendforensics/dividendforensics-com/blob/main/docs/EXPANSION-RELEASE-2026-10-18.md
디자인 검수 기록: https://github.com/dividendforensics/dividendforensics-com/blob/f3af0fb0a836e38986dd8daf984f881ef4043c42/docs/DESIGN-REVIEW-2026-10-18.md

기존 DFB를 무료 REIT 교육·계산기·공시 기반 리서치 사이트로 확장했습니다. 교육은 REIT에 집중하지만 리서치 범위는 REIT/BDC에만 한정하지 않습니다. 향후 멤버십은 별도 계획이며 현재 가입·결제는 열려 있지 않습니다. 운영자의 목표는 무료 교육으로 독자를 확보하고 AdSense 수익화를 준비하는 것입니다. 현재 AdSense 게시자 ID가 없고 광고가 송출되는 상태는 아닙니다.

실제 구현 범위:

- **교육 원고 36편**: 초급 6, 중급 18, 고급 8, 전문가 4. REIT 구조, 분배 규정, 넷리스·아파트·물류·오피스·데이터센터 등 사업, FFO·AFFO·NOI·NAV, 부채·희석·배당 삭감 등을 각각 독립 페이지로 구성했습니다.
- **4단계 과정**: 선행 지식·학습 목표·순서·적용 과제·확인 퀴즈가 있습니다. Expert는 자료의 깊이를 뜻하며 자격·공인 인증을 의미하지 않습니다.
- **기존 계산기 7개**: 배당 수입, 재투자, AFFO 지급률/스트레스, FFO→AFFO 조정, NAV/캡레이트, 재융자, 총수익. 수식·가상 예제·한계·CSV 다운로드가 있고 입력은 브라우저 안에서 계산합니다.
- **검색·탐색**: 홈 검색에서 교육 허브로 이동하며, 허브에 검색·주제·난이도 필터가 있습니다. 용어 25개의 검색 가능한 용어집, 출처 목록, 편집 방침도 있습니다.
- **설명 도해 4개**: property atlas, cash-flow bridge, capital stack, evidence desk. 개념·가상 예시이며 실제 기업 데이터나 실사로 표현하지 않습니다. 웹용 WebP에 크기 속성을 지정했습니다.
- **디자인 개정**: Tabler·Tremor의 정보 위계와 숫자 가독성을 참고한 DFB 전용 정적 HTML/CSS입니다. 네이비·아이보리·브라스, 큰 세리프 제목, 밝은 읽기 화면, 짙은 계산 결과 패널, 공통 읽기 메뉴를 적용했습니다. 템플릿의 데모 방문자 수·수익·시장 수치 같은 가짜 실적은 추가하지 않았습니다.
- **리서치 아카이브**: 확인된 선택 기록 20건. 이번에 Ready Capital(9/22), Millrose(9/23), CoreWeave(9/25)를 실제 Benzinga 원문과 대조해 추가했습니다. 선택 아카이브의 최신 날짜는 25 Sep 2026이며 전체 발행 건수를 주장하지 않습니다.
- **검색용 구성**: 정적 본문, 제목·설명·canonical, Article/Breadcrumb, 사이트맵. 활성 HTML 87개, 사이트맵 URL 75개입니다. 404.html·membership.html·breakbefore.html은 및 짧은 출처 안내 case-* 9개를 의도적으로 제외했습니다. noindex는 광고 정책 예외가 아닙니다. Google 확인 파일과 과거 리디렉션은 활성 콘텐츠 수에 포함하지 않습니다.
- **기존 URL 보존**: 기존 입문 글의 7월 발행일을 보존했습니다. 환불 정책 canonical은 `/refund-policy.html`, 기존 `/Refund.html`은 이동 안내로 남겼습니다. 기존 무료 보고서 전달과 문의 폼도 유지했습니다.

- **새 BDC 도구 5개**: NII/PIK/정규·추가·특별 배당, PIK 분모 비교, non-accrual 원가/공정가치, NAV 할인·프리미엄, 부채/자본. 보고·조정 기준과 기간·단위·출처를 보존하고 미확인 값과 0을 구분합니다.
- **자본 도구 3개**: JV 지분별 부채와 연결 중복, 만기별 유동성 부족, 우선주 차감 전/후 보통주 귀속. decimal.js 10.6.0(MIT) 원본과 라이선스를 포함했고 CSV는 로컬 처리합니다.
- **수동 공시 검수 파이프라인**: scripts/filing_review.py는 수집·중복/정정·검수·명시적 내보내기 틀입니다. 실제 CIK와 User-Agent는 미설정입니다. SEC 실데이터·자동 게시·일정·메일은 활성화하지 않았습니다.
- **선별적 유료 제안 창구**: 보수·통화·범위·일정·지급·수정·사용권·독점 조건을 받습니다. 일반 질문에는 프로젝트 조건을 요구하지 않습니다. 모의 서비스 응답 검사만 수행하며 실제 Gmail 수신은 미확인입니다. 검토자는 실제 제출하지 마세요.

새 도구 핵심 재계산: NII120/PIK18/총투자수익180, 배당100+10+5=115 → coverage1.2 및1.043478, PIK비중10%와15%; PIK 민감도120/115.5/111/102. JV800+500×40%+400×25%=1100, 보증100별도. 유동성40+30=70, 만기90후−20, 의무지출10후−30. 알 수 없는 값·연결 중복·회계연도와 실제 날짜·이미 우선주 차감한 수치를 특히 검토해 주세요.

제작 기록은 보관하되 공개 화면에서 AI 제작 방식을 먼저 언급하지 않는 것은 사용자가 직접 선택한 방침입니다. 도해가 개념·가상 예시라는 설명은 유지합니다. 이를 허위 인간 검토나 가짜 전문가 인증으로 바꾸지 않았는지 확인해 주세요. 플랫폼별 필수 고지나 법적 요구가 실제로 적용된다고 판단한다면 관할·적용 조건·공식 근거를 제시하고, 확인하지 않은 의무를 단정하지 마세요.

## 2. 바로 확인할 공개 URL

- 전체 도구15개: https://dividendforensics.com/tools.html
- BDC NII/PIK: https://dividendforensics.com/calculator-bdc-nii-pik.html
- JV 부채: https://dividendforensics.com/calculator-jv-debt.html
- 만기 유동성: https://dividendforensics.com/calculator-debt-ladder.html
- 우선주 귀속: https://dividendforensics.com/calculator-preferred-common.html
- 선별적 의뢰: https://dividendforensics.com/research-desk.html#inquiries
- 홈: https://dividendforensics.com/
- 교육 허브: https://dividendforensics.com/learn.html
- 초급: https://dividendforensics.com/course-beginner.html
- 중급: https://dividendforensics.com/course-intermediate.html
- 고급: https://dividendforensics.com/course-advanced.html
- 전문가: https://dividendforensics.com/course-expert.html
- 넷리스: https://dividendforensics.com/learn-net-lease.html
- FFO: https://dividendforensics.com/learn-ffo.html
- AFFO: https://dividendforensics.com/learn-affo.html
- 배당 규정: https://dividendforensics.com/learn-distribution-rule.html
- 전문가 실습: `/learn-expert-affo-normalization.html`, `/learn-expert-jv-nav.html`, `/learn-expert-refinancing-model.html`, `/learn-expert-investment-memo.html`
- 도구 목록: https://dividendforensics.com/tools.html
- 용어집: https://dividendforensics.com/glossary.html
- 리서치: https://dividendforensics.com/research.html
- 방법론: https://dividendforensics.com/methodology.html
- 출처: https://dividendforensics.com/sources.html
- 편집 방침: https://dividendforensics.com/editorial-policy.html
- 개인정보: https://dividendforensics.com/privacy.html
- 사이트맵: https://dividendforensics.com/sitemap.xml

계산기 7개: `/calculator-dividend-income.html`, `/calculator-reinvestment.html`, `/calculator-payout-ratio.html`, `/calculator-ffo-affo.html`, `/calculator-nav.html`, `/calculator-refinancing.html`, `/calculator-total-return.html`.

## 3. 요청하는 검토

1. **독자 경험·디자인**: 고급스럽고 일관된 금융 사이트로 읽히는지, 초보자가 어디서 시작할지 알 수 있는지, 어두운 화면·글자 크기·긴 글·숫자·검색·모바일 메뉴가 읽기 쉬운지 확인해 주세요. 데스크톱과 320/390px 모바일에서 가로 넘침·잘림·포커스·터치 영역도 봐 주세요. 미적 취향과 실제 사용 장애를 구분해 주세요.
2. **영어의 의미와 금융 개념**: 문법보다 뜻이 잘못 전달되는 문장을 우선해 주세요. 사업 유형/상장 여부, 가격/배당금/수익률, 회계/현금, FFO/AFFO/NOI/NAV, 90% 과세소득 분배 규정, Buffer Half-Life/전액 소진을 혼동하는지 봐 주세요. 전문가 원고 4편의 수치를 독립적으로 다시 계산해 주세요.
3. **계산기**: 실제 소스와 화면을 확인해 단위·퍼센트 입력(5=5%)·연간/월말 시점·원천징수·수수료·분모·0값·음수·CSV가 일치하는지 봐 주세요. 주요 재현: AFFO −4, 배당 3, 하락 25% → 시나리오 AFFO −5, cushion −8, 지급률 `Not defined`. AFFO 0은 0 유지. 총수익 분모에 매수 수수료 포함. 재투자에도 원천징수 가정이 있습니다.
4. **SEO·코드·배포**: 실제 화면과 title/description/canonical/Breadcrumb/수정일이 일치하는지, 허브가 자기 자신을 Breadcrumb에 중복하는지, 계산기가 `Home → Calculators → 계산기`로 표시되는지, JS 없이 교육 본문을 읽을 수 있는지 확인해 주세요. sitemap 제외 기본 3개와 case-* 9개와 기존 URL 이동도 확인해 주세요.
5. **근거와 정책**: 인용 링크·기업 공시·날짜·도해·발행 이력이 실제 근거와 맞는지, 과장된 전문성·수익/승인 보장·가짜 인간 검토·유사 글 양산이 있는지 봐 주세요. 계정 접근이 필요한 AdSense/Search Console/분석 미확인 사항과 공개 사이트의 확정 결함은 분리해 주세요.

주요 소스 경로: `templates/home.html`, `templates/header.html`, `templates/footer.html`, `bureau.css`, `build_site.py`, `education.py`, `curriculum.py`, `education.js`, `calculators.js`, `bdc_tools.py`, `bdc-calculators.js`, `capital_tools.py`, `capital-calculators.js`, `proposal.js`, `scripts/filing_review.py`, `vendor/manifest.json`, `content/foundations.json`, `content/sectors.json`, `content/metrics.json`, `content/expert.json`, `articles.json`.

검증 명령: `python build_site.py --check`, `python -m unittest discover -s tests`, `node --test tests/*.test.cjs`, `python tools/check_site.py`, `python tools/education_browser_check.py`. 브라우저 검사는 Playwright/Chromium이 필요합니다. 현재 검증 기록은 Python 77개, Node 55개, 87페이지 정적 검사; 로컬 인라인261회 렌더링 통과(87×320/390/1440), 실제 HTTP 교육 기능 재검사 통과. GitHub CI435회 렌더링 통과(87×5너비), 공개97응답 일치. 세부 범위는 릴리스 문서 확인입니다. 실제로 재실행하지 않았다면 이 숫자를 본인의 검증 결과로 합산하지 마세요.

## 4. 반드시 구분해 주세요

- 문서만 읽었는지, HTML을 봤는지, 소스를 봤는지, 브라우저를 조작했는지, 직접 계산했는지 먼저 적어 주세요.
- 검색 결과의 오래된 스니펫만으로 배포 실패·404를 확정하지 마세요. 직접 HTTP 응답과 캐시 우회 재조회, 해당 버전 소스를 대조해 주세요. 그래도 확인할 수 없으면 미확인으로 남겨 주세요.
- 템플릿 표식(`editorial-20260917`)은 발행일이 아닙니다. 기존 입문 글의 7/30·7/31 발행일과 새 교육 36편의 10/18 발행일을 구분해 주세요.
- 월까지만 확인된 발행일에 임의로 일을 붙이지 마세요. 메타데이터의 ISO 날짜와 사람이 읽는 표시 형식의 차이도 그 자체로 오류는 아닙니다.
- 실제 확인한 결함과 개선 아이디어를 구분하고, 확인하지 못한 범위를 구체적으로 적어 주세요.
- 계정 없이 Google 색인 상태나 AdSense 승인 상태를 확정하지 마세요. 승인·수익·검색 순위를 보장하지 마세요.

## 5. 피드백 형식

먼저 검토 범위와 도구 한계를 설명한 뒤, 문제를 다음 표로 제시해 주세요.

| 심각도 | 페이지/파일·위치 | 실제 관찰·원문 | 왜 문제인지 | 재현 절차·입력 | 구체적 수정안 | 근거 URL/검증 방법 |
| --- | --- | --- | --- | --- | --- | --- |

심각도는 P0(긴급한 보안/데이터 사고), P1(핵심 기능 고장·중대한 금융 오해), P2(기능/내용/탐색/메타데이터의 명확한 결함), P3(경미한 표현·가독성·개선)로 분류해 주세요. 코드/화면을 확인하지 못한 추정은 확정 결함 목록과 분리해 주세요.

마지막에는 **출시 차단 문제**, **즉시 수정할 문제**, **후속 콘텐츠 개선**, **운영자 계정 작업**, **미검수 범위**를 구분해 주세요. 문제가 없으면 검수한 범위 내에서 없다고 답해도 됩니다. 저장소 수정·배포·이메일 발송·폼 제출·가입·결제는 하지 말고 검토 결과만 주세요.

---

## 여러 AI에게 나눠 맡길 때 덧붙일 초점

**금융·계산 담당:** 전문가 실습 4편과 기존 7개와 새 8개 도구의 산식·단위·시점·세금·수수료·음수/0값을 우선해 주세요. 예시 수치를 직접 재계산하고 issuer-defined AFFO와 실제 현금흐름·법정 분배 요건의 차이를 봐 주세요.

**디자인·독자 경험 담당:** 홈·교육 허브·긴 교육 글·과정·계산기·리서치의 데스크톱/모바일 경험을 우선해 주세요. 읽기 쉬움·발견 가능성·메뉴·키보드 조작·색 대비를 실제 화면에서 확인하고 위치를 특정해 주세요.

**SEO·콘텐츠 신뢰 담당:** raw HTML·canonical·Breadcrumb·날짜·사이트맵·구 URL 이동·출처·발행 이력을 우선해 주세요. 실제 사이트 상태와 검색 캐시·계정 미확인을 분리해 주세요.
