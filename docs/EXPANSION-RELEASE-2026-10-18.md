# DFB 무료 분석 도구 확장 — 2026-10-18

## 구현과 현재 상태
디자인 PR #3은 main에 병합되었다. 이번 확장본은 별도 변경으로 검증 중이며, 아래 배포 기록이 완료되기 전에는 공개 설치 완료로 해석하지 않는다.

- REIT 교육36편과4단계 과정, 기존7계산기는 유지하고 BDC5개·JV/만기/우선주3개를 추가: 총15도구.
- 87활성 HTML, 사이트맵75 URL. 기존9개 case 안내 페이지는 noindex,follow로 색인 제외하고 아카이브는 원문으로 직접 연결. 광고를 넣어도 된다는 정책 예외가 아님. 원문 재게시 권리를 가정하지 않음.
- 모든 새 도구에 산식·합성 예제·입력 단위/기간/기준·출처 입력·한계·CSV를 제공. 알 수 없는 값은0으로 바꾸지 않음. 점수·매수추천·배당 안전 판정 없음.
- decimal.js10.6.0 MIT 원본·LICENSE·npm 무결성·파일 해시를 vendor/에 보관. 검증된 라이브러리라는 보안 보증은 아님. 표와 기존 검색을 재사용하여 Chart.js/Papa Parse/Tabulator를 불필요하게 설치하지 않음.
- 실제 SEC 메타데이터 수집은 수동 CLI 틀로 분리. 자동 일정/메일/게시 없음. 실제 CIK/User-Agent 미설정, 실공시 수치 자동 수집 미실행. 세부 운영은 FILING-REVIEW.md.
- 실제 Benzinga/Muck Rack 저자 링크와 Person ID 연결. 해당 매체의 보증·고용·전문 자격으로 표현하지 않음. 날짜 없는 일괄 보유상태 주장은 제거하고 각 원문 시점의 고지로 안내.
- 유료 의뢰는 제안을 받고 선별 검토. 범위·보수·통화·일정·지급·수정·사용권·독점 조건. 일반 질문에는 해당 조건을 요구하지 않음. 회사명 선택, 개인정보 확인 미선택 기본값. 기존 FormSubmit 엔드포인트 유지. 실제 수신 미확인 안내와 이메일 대안 유지.

## 검증 근거
- Python77개, Node55개 통과. 정적87페이지 링크/자산/앵커/canonical/폼 검사 통과.
- 별도 담당자가 BDC5×3화면15회, 자본도구3×3화면9회 기능 검사. 최종 통합 화면 검사는 진행 중.
- 제안 폼 mock9항목 통과, 모의 제출3회, 실제 외부 요청0회. 서비스 접수는 이메일 배달/의뢰 수락과 구별. 실제 Gmail 수신, 실제20초 timeout, 화면낭독기 검수 미실행.
- 독립 통합 소스 검토: P1/P2 없음. 대소문자 저자명 정리, 자본도구 입력 변경 시 이전 결과 지움 반영.

## 미완료·경계
AdSense ID·광고·CMP·Search Console·GA4 미연결. 승인/수익 보장 없음. 실제 회사 데이터는 검토된 자료를 따로 준비해야 함. 호스팅 상업 용도 약관 확인/이전 선택은 TOOLS-RESEARCH-2026-10-18.md를 참고. 사이트 접수창을 열었다고 서비스 계약/결제를 활성화한 것은 아님.

사용자가 지정한 C:/Users/User/Downloads/SITE_AUDIT_FIXES.md는 이번 파일시스템에서 발견되지 않았고 Downloads와 대화 첨부 디렉터리 검색에도 일치 파일이 없었다. 이 파일의 내용을 확인·반영했다고 주장하지 않는다.

## 호스팅 확인 요청 초안 — 미발송
GitHub Support에 보낼 경우 운영자가 검토할 문안:

> We host dividendforensics.com on GitHub Pages as a free financial education publication with browser-local worksheets. No membership enrollment, payment processing or SaaS accounts are active. We plan to apply for display advertising and selectively receive paid research or content-licensing proposals through an external form service. Could you confirm whether this intended use fits the current GitHub Pages usage limits? If not, we will move production hosting before activating commercial features. We request clarification rather than assume advertising is explicitly permitted.

발송/이전/DNS 변경은 수행하지 않았다. 무료 대체 호스팅도 상업 이용 약관을 별도로 확인해야 함.

## 후속 독립 검토
INDEPENDENT-REVIEW-PROMPT.md를 다른 AI에게 전달. 해당 AI가 실제 본 범위와 소스/화면/직접 계산을 구분하고 심각도·위치·재현·수정안을 회신하도록 구성.
