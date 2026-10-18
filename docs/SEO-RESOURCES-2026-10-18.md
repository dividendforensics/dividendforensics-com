# 실용 가이드·배당 리서치 워크시트 확장 — 2026-10-18

## 구현한 공개 내용

1. `/reit-vs-bdc.html`: 미국 equity REIT와 lending-focused BDC의 사업·FFO/AFFO/NII·가치·자금조달 차이. 같은8%수익률의 서로 다른 근거를 가상 수치로 비교한다. mortgage REIT는 별도 범위라고 명시한다.
2. `/dividend-dates.html`: 선언일/배당락일/기준일/지급일, 현재T+1과큰분배예외, 가상 일정, 배당포착의총수익예제. 실시간 배당일정이나매매추천을제공하지않는다.
3. `/dividend-research-worksheet.html`: 공시입력위치표, 근거→조정→가정→미확인사항의 연구 흐름,12개 입력칸,로컬TXT다운로드,긴메모전체인쇄/PDF. 서버전송·저장·가입없음. JS비활성시Enter로GET제출될수있는form요소를사용하지않는다. 빈칸은Not recorded이며0으로대체하지않는다.

홈·REIT/BDC학습실·도구목록·관련입문글에서정적링크로연결. 기존52개과정글과별도3개실용자료다. 활성HTML119개/사이트맵107개/계산도구15개. 생성원본은`research_resources.py`와`templates/resources/`이며다음빌드에서도유지된다. canonical,Article/Breadcrumb,발행·수정일과sitemap lastmod를생성한다. 번역하지않은페이지에hreflang을추가하지않는다.

메타태그·ads.txt소유권확인은유지한다. 광고스크립트는추가하지않는다. 개인정보안내에연구메모의로컬다운로드/인쇄처리를반영했다.

## 조사 근거와 범위

- Google사람중심콘텐츠: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Google내부링크: https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- SEC투자자자료REIT: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-65
- SEC BDC: https://www.investor.gov/introduction-investing/investing-basics/investment-products/closed-end-funds/publicly-traded-business-development-companies-bdcs
- Nareit FFO/AFFO: https://www.reit.com/glossary/funds-operation-ffo 및 https://www.reit.com/glossary/adjusted-funds-operations-affo
- SEC 배당일: https://www.investor.gov/introduction-investing/investing-basics/glossary/ex-dividend-dates-when-are-you-entitled-stock-and
- FINRA11140: https://www.finra.org/rules-guidance/rulebooks/finra-rules/11140
- SEC공시읽기: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/how-read

위자료는2026-10-18확인했다. 검색어별수요량·경쟁도·실제GSC성과를측정한것은아니다. 검색질문과기존학습흐름의공백을기준으로선정했으며순위나승인향상을보장하지않는다. 수치예제/연구양식은가상교육자료로만표시한다.

## 직접 확인한 로컬 결과

- Python117개통과,119개활성페이지링크/앵커/자산검사통과,SEO107개URL오류0. 기존긴제목/설명편집권고2개는순위결함으로판정하지않는다.
- Chrome320/390/1440px×신규3페이지=9회렌더:가로넘침없음. 데스크톱/모바일스크린샷확인.
- 실제TXT다운로드:한글외문자·줄바꿈·따옴표·HTML처럼보이는문자열·긴메모유지. textContent사용으로입력HTML을실행하지않음.
- 인쇄모드에서입력칸대신전체텍스트확인·PDF생성. JS없는본문·입력·Enter미전송확인. 자동저장없음/리로드시초기화/저장소·쿠키·비GET요청0확인. 입력칸키보드이동확인.
- Decimal별도계산:8%,80%,90.91%,1.20×,1.0435×,0.9652×;가상일정요일검산.
- 새브라우저검사는`tools/resources_browser_check.py`와PR CI에포함했다. 배포대조는신규3페이지/2자산을포함해총137개를검사하도록확장했다.

## 다른 AI에게 요청할 집중 검토

위3개공개페이지와생성원본을읽고,직접확인/실행/계산/미확인을구분해한국어로피드백해달라. 문서의검사수를직접실행실적으로합산하지말것.

- REIT/BDC경계,PIK/NII와현금흐름구분,같은수익률예제의반복투자이중차감여부.
- T+1보통배당일과25%이상/특별분배/비영업일예외. 가상일정이실제회사일정으로읽히지않는지.
- 워크시트정보가네트워크로전송되거나자동저장되는지,TXT/긴메모인쇄누락,JS비활성Enter동작,입력문자열의HTML실행여부.
- 320/390/1440폭표스크롤·키보드·다운로드,정적본문·canonical/Article날짜/sitemap107·기존EN/ES7쌍유지.
- 새페이지를발견할내부링크와기존글과의실질적차이. 검색량/순위보장·가짜검토주장여부.

문제는P0~P3/파일·URL/원문/재현입력/영향/수정제안으로기록한다. 계정작업·외부폼제출·메일·결제·SEC실수집·저장소수정은실행하지말것. 실제Google색인·광고심사결과는이번코드검사로확정하지않는다.
