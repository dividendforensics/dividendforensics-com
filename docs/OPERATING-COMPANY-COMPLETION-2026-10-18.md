# DFB PR15 완료 기록 — 2026-10-18

## 완료 상태

PR #15가 병합·배포되었다. 일반 기업 학습 경로 5페이지, Apple FY2024 공시 실습, 시나리오 비교·CSV를 갖춘 현금흐름 작업 화면을 공개했다. REIT·BDC·다국어 콘텐츠와 AdSense 소유권 확인 정보는 유지했다.

- PR: https://github.com/dividendforensics/dividendforensics-com/pull/15
- 제품 커밋: `d9b4415bcc5c02438bc3bebe1bf86e54303185db`
- 검증한 Git tree: `28051324777984c5534b85e49c0e4bddaa9fe6d5` (로컬·PR·병합 제품 일치)
- CI: https://github.com/dividendforensics/dividendforensics-com/actions/runs/39127112481 — 성공
- Build and Publish: https://github.com/dividendforensics/dividendforensics-com/actions/runs/39128054775 — 성공
- 제품 Pages (`d9b4415…`): https://github.com/dividendforensics/dividendforensics-com/actions/runs/39128081201 — 성공
- 후속 완료 기록만 바뀐 커밋 `a51d210…`의 Pages: https://github.com/dividendforensics/dividendforensics-com/actions/runs/39128251106 — 성공. 두 커밋 사이 변경은 이 완료 문서 한 파일이다.
- 초기 Pages 작업 39128054673은 명시적 재빌드로 대체되어 취소됐다. 제품 배포 및 후속 문서 배포와 구분한다. 이 구분은 2026-10-19 실행 기록을 재조회해 보완했다.

## 새로 이용할 수 있는 기능

1. [일반 기업 학습 입구](https://dividendforensics.com/operating-companies.html)
2. [순이익에서 영업현금흐름으로](https://dividendforensics.com/operating-cash-flow-guide.html)
3. [배당·자사주 매입·잔여 현금](https://dividendforensics.com/dividends-buybacks-guide.html)
4. [Apple FY2024 실제 공시 실습](https://dividendforensics.com/filing-lab-apple-2024.html)
5. [Apple 값을 불러온 현금흐름 작업 화면](https://dividendforensics.com/cash-flow-workbench.html?example=apple-2024)

작업 화면은 입력 변경 → 도표·정확한 표 갱신 → 기준 시나리오 보관 → 차이 비교 → 출처·가정 포함 CSV 다운로드까지 연결된다. 기말 현금 대사는 FCF/주주 지급 잔여액과 별도 계산한다. 입력을 서버로 전송하거나 저장하지 않는다. 새로고침하면 수정과 기준 시나리오가 사라진다.

## 이번에 직접 실행한 검증

| 범위 | 결과 |
|---|---|
| 전체 Python | 로컬 및 GitHub CI 156개 통과 |
| 전체 Node | 로컬 및 GitHub CI 95개 통과 |
| 정적 구조 | 활성 HTML 145개, 내부 링크·자산·앵커 검사 통과 |
| SEO | 사이트맵 133개, 오류 0개; 기존 제목/설명 길이 권고 2개 |
| 전체 화면 | GitHub CI 145페이지 × 320/390/768/1024/1440px = 725 렌더 통과 |
| 새 경로 | 로컬 및 CI 5페이지 × 5폭 = 25 렌더, 실제 동작 8항목 통과 |
| 계산기 실패 방어 | 로컬 및 CI 21계산기·68개 실패 조건 통과, 비활성 컨트롤 클릭/Enter 뒤 요청 0 |
| 기존 계산 품질 | 8개 브라우저 회귀 통과; 파일 선택 CSV 왕복·미세 금액·FFO 소계·오류 복구 포함 |
| 공개 배포 대조 | 일반 공개 URL 170/170이 검증한 제품 파일과 일치 |

전체 725 렌더와 특화 25 렌더는 별도 실행이다. 이전 리뷰의 수치와 합산하지 않았다. 공개 응답은 줄바꿈 LF 정규화 및 앞뒤 공백 제거 후 비교했다. 캐시 우회 응답으로 일반 URL 불일치를 통과시키지 않았다. 배포 도중 시작한 1차 조회에는 이전 버전이 있었고, 배포 완료 후 2차 조회에서 일반 URL 전체가 일치했다.

브라우저의 Apple preset 로딩 완료를 기다리도록 통합 검사 하네스를 고쳤고, 실패 방어 검사에서는 지연된 favicon 요청을 사용자 조작의 전송으로 오인하지 않도록 초기 network-idle을 기다리게 했다. 제품의 전송 결함으로 기록하지 않는다.

로컬 근거: `.qa/pr15-ci-job.log`, `.qa/pr15-node.txt`, `.qa/operating-browser.json`, `.qa/calculator-safety.json`, `.qa/calculator-quality-browser.json`, `.qa/pr15-live.json`. `.qa`는 배포하지 않는다. 과거 `pr15-live.json`에는 커밋·실행 시각·Actions 실행 연결이 없으므로 170/170은 당시 로컬 관측으로 한정한다. 이후 자동 검증의 공개 Actions artifact와 동일한 증거로 취급하지 않는다.

## 내용·기능 보강

- Apple 원문 입력 36개와 ARCC 분기 배당 입력 추가 8개를 대조했다. 기존 두 실습 원장은 63개, 세 실습 전체 원문 입력은 99개다.
- Apple의 현금 배당과 선언 배당, 현금 매입과 자본 변동, 총매입과 순주식 수 감소를 구분했다.
- 원문에 별도 FX 행이 없는 경우의 0 입력을 실습 관례로 명시하고 CSV와 기준값에도 남겼다.
- ARCC 정규 배당 분류는 연간 10-K의 네 분기 전체 표를 근거로 보강했다.
- 미세 금액 일반 소수 표시, FFO/AFFO 구성·소계의 정확한 표시, 입력 앞 PIK 설명, 스크립트 버전 갱신을 완료했다.
- 세 Astra xhigh 내부 에이전트가 계산 품질, 일반 기업 도구, SEC 공시 실습을 나누어 구현·교차 검토했다. 배포는 위 실제 검사 결과를 확인한 뒤 진행했다.

구현 설명: `OPERATING-COMPANY-RELEASE-2026-10-18.md`. Apple 원문 대조: `OPERATING-COMPANY-SOURCE-AUDIT-2026-10-18.md`.

## 확인하지 않은 것

Google의 실제 색인·노출·순위, AdSense 심사 결과·수익, 실제 메일 수신, 실폰·스크린리더·원어민 감수는 확인하지 않았다. 자동 SEC 갱신과 광고 송출을 활성화하지 않았다. 사이트맵 133개는 Google 색인 133개라는 뜻이 아니다. 이번 검사 범위에서 출시를 막는 미해결 결함은 없지만, 모든 환경에서 완벽하거나 AdSense 승인이 보장된다고 주장하지 않는다.

