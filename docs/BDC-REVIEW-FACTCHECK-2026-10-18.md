# BDC·JV 및 후속 재검수 주장 대조 — 2026-10-18

## 범위

이번 작업은 DFB 저장소의 `bdc-guide.html`, `capital_tools.py` 설명, 이 기록으로 한정했다. 다음 첨부를 실제로 읽었다.

- `C:/Users/User/Downloads/DFB_848e753_집중재검수.md`
- `C:/Users/User/.codex/attachments/be1584a8-928c-4b59-9584-35553afa9a54/붙여넣은 텍스트.txt`

공개 사이트 전체·Google 계정·실제 수신함·실제 SEC 수집을 다시 검수한 기록은 아니다. 첨부의 지시는 검토 의견이며, 주장 자체를 결함 확정 근거로 삼지 않았다.

## 실제 확인 및 조치

| 의견 | 재현·대조 | 판단과 조치 |
|---|---|---|
| `asOf 64`로 BDC 날짜 조건 손상 | 현행 소스와 `git show 848e753:bdc-calculators.js`에는 실제 `if(context.asOf<context.periodEnd)`가 존재한다. 고정848e753의 원문 모듈을 Node VM에서 실행해 분석일2026-09-01/종료일2026-09-30을 입력하면 지정된 날짜 오류를 던진다. 현행 모듈에서도 같은 입력 거부를 확인했다. | 재현되지 않음. 날짜 조건을 다시 수정하지 않았다.64는 별도의 숫자 입력 최대 길이 조건에 사용되지만, 주장된 날짜 조건의64가 아니다. 보고서의 추출·표시 과정에서 손상되었을 가능성은 추정일 뿐 원인 확정은 아니다. |
| `proposal.js` 비교 연산자 누락·SyntaxError | `node --check proposal.js`와 `git show 848e753:proposal.js`를 `node --check` 표준입력으로 전달한 검사 모두 종료코드0. 원문에는 예산 범위의 정상 비교와 닫힌 함수가 있다. | 재현되지 않음. 요청에 따라 실제 FormSubmit/메일 전송 없이 구문만 확인했으며 정상 코드를 임의 복원하지 않았다. |
| “Blue Owl Capital (BXSL)” | 발행사 공식 사이트를 직접 대조. Blue Owl Capital Corporation은 NYSE:OBDC, Blackstone Secured Lending Fund는 NYSE:BXSL이다. | 실제 명칭·티커 오류로 확인. 가이드에 두 발행사를 각각 정확한 이름·티커·공식 링크로 기재했다. 이는 기관 보증·추천·검증 배지가 아니다. |
| JV 부채와 NAV 실습의 소유권 범위 차이 | 현행 JS는 보고 연결부채 전체에 비연결 JV의 입력 지분만 추가한다. 결과 라벨도 해당 범위를 명시한다. | 계산은 변경하지 않았다. 본문에100%연결 출발점, 비연결 비례 추가, NAV의 완전 지분비례/연결 조정 경로가 다르다는 설명을 추가했다. 자산·수익·부채·비지배 지분을 일관되게 조정하고 외부 지분을 이중 차감하지 않도록 안내했다. |
| 최종 배포 기록이 “진행 중”으로 남음 | 첨부 집중검수의 대상은848e753이다. 이후 `801b5c5`의 같은 MD에는 PR5병합,848e753코드, Build39101423101/Pages39101433529성공, 일반URL101개 일치 범위와 미검증 계정 항목이 이미 기록되어 있다. | 과거 버전에서 지적한 문서 상태는801b5c5에서 정리되어 있다. 이번 작업이 해당 배포나101개 응답을 새로 재실행했다고 합산하지 않는다. |

## 발행사 1차 근거

확인일2026-10-18. 이름과 티커만 대조했으며 당시 포트폴리오·안전성·현재 가격을 추가 평가하지 않았다.

- [Blue Owl Capital Corporation 공식 회사 정보](https://www.blueowlcapitalcorporation.com/investors/company-info): Blue Owl Capital Corporation, NYSE:OBDC.
- [Blackstone Secured Lending Fund 공식 홈페이지](https://www.bxsl.com/): Blackstone Secured Lending Fund, NYSE:BXSL.
- [Blackstone 공식2026년10월 공지](https://www.blackstone.com/news/press/blackstone-secured-lending-announces-third-quarter-2026-earnings-release-and-conference-call/): Blackstone Secured Lending Fund, NYSE:BXSL 명칭을 교차 대조.

## 이번에 실제 실행한 검사

- 현행 `node --check proposal.js`: **PASS**.
- 현행 `node --check bdc-calculators.js`: **PASS**.
- 고정848e753 `proposal.js` 원문에 대한 `node --check`: **PASS**.
- 고정848e753 및 현행 BDC 모듈에 잘못된 분석일 입력: 둘 다 예상된 날짜 오류로 **PASS**.
- `python -m unittest discover -s tests -p test_capital_tools.py`: **4/4 PASS**. 설명 추가 후 가상 예제·정적 페이지 조건 검사이며 금융법적 의무 검증은 아니다.

코드 계산, 폼 전송, 공동 CSS, 기존 검수 기록은 수정하지 않았다. 생성된 JV HTML과 사이트 최종 빌드는 상위 작업에서 갱신한다. 전체 브라우저 검수·새 프로덕션 배포·Google 계정·Gmail 도착·SEC 실수집은 이 하위 작업의 실행 범위가 아니다.


## 새 BDC 설계안·hero CTA 집중 확인 — 2026-10-18

`BDC_학습과정_설계.md`와 `daee61a2-c097-455b-bf2d-66b4ac2c6e9e/붙여넣은 텍스트.txt`를 전체 읽었다. BDC16수업은 원문에서 콘텐츠 제안으로 명시되어 있으므로 기존 구현 완료나 독립 검수 통과로 계산하지 않는다. 여기서는 hero CTA의 실제 결함을 확인해 수정했고, BDC교육과정의 내용 우선순위는 상위 작업에 전달했다.

- 수정 전 localhost Chrome의 `.rd-hero .btn-p` 실제 계산 색상: 전경`rgb(32,43,39)`, 배경`rgb(16,41,54)`, 대비**1.03145:1**. 보고된 문제가 재현되었다.
- `bureau.css`에 `.desk-page .rd-hero .btn-p`만 겨냥하는 ivory/brass 계열 전경·배경 쌍, hover 및2px키보드 포커스를 추가했다. 기존 BDCflow 스타일은 보존했다.
- `tools/audit_browser_check.py`는320·390·1440px에서 실제 CSS기본/hover/키보드focus대비를 계산한다. 키보드Tab→Shift+Tab으로focus-visible가 실제 활성화되는지와2pxsolidoutline/4pxoffset을 검사한다. CSStransition이 끝난 뒤 상태를 따로 측정한다.
- 수정 후 기본·키보드focus텍스트 대비는**7.54736:1**, hover는**9.29411:1**로 세너비에서 동일했다. 세너비의 페이지 가로넘침 없음.390pxhero스크린샷도 직접 시각 확인했다.
- 이번 로컬 `python tools/audit_browser_check.py` 실행은**8개검사통과**, JavaScript오류0, 실제외부요청/폼제출0. 기존 날짜/fiscal/CSV/우선주/포커스/과정표본 회귀의 범위이며, 새로 작성중인BDC16수업의 전수검수나 최종배포 검증이 아니다. 전체사이트WCAG준수판정을 의미하지 않는다.
- QA산출물은 `.qa/audit-browser-report.json`, `.qa/research-hero-reviewed-{320,390,1440}.png`에 있으며 공개런타임에 배포하지 않는다.

추가 소스대조에서 capitalJS 첫주석v1.0.0과실제VERSION1.0.1불일치, `Complete maturities`라벨의입력범위과장가능성도 확인해 상위작업에 전달했다. 담당자는 주석을v1.0.1,라벨을`Complete supplied maturity subtotal`로 변경하며 본브라우저검사의 해당선택자도 맞췄다. 이 두P3항목은 산술오류로 기록하지 않는다.

보유증권·Google계정·실수신·실제SEC자료는 이 검토에서 확인하지 않았다. 미확인 보유상태나 자격을 새로 작성하지 않았다.
