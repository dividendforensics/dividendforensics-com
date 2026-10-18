# DFB 교육 사이트 운영 가이드

기준일: 2026-10-18. 현재 무료 교육 사이트는 REIT36편·BDC16편, 계산기15개, 스페인어 초기판7페이지와 사이트맵107개 URL을 갖췄다. 멤버십 가입·결제는 열지 않는다. 운영자가 실제 게시자 ID `ca-pub-3030006828946894`를 제공하여 홈페이지 소유권 확인 메타 태그와 루트 ads.txt를 추가했다. 광고 스크립트·광고 슬롯은 활성화하지 않았다. AdSense 계정 안의 소유권 확인·검토 요청·승인은 별도이며 아직 확인되지 않았다.

## SEO는 어디서 보는가

1. [Google Search Console](https://search.google.com/search-console)에 실제 사이트를 소유한 Google 계정으로 로그인한다. `dividendforensics.com` 도메인 속성을 선택한다. 없다면 도메인 속성을 만들고 DNS 소유권을 확인한다. Domain 속성은 DNS로 확인한다. 기존 Google HTML 확인 파일은 URL-prefix 속성에 사용하는 별도 방법이며 Domain 속성의 DNS 확인을 대신하지 않는다. 파일이 있다는 것만으로 현재 계정의 소유권 확인 성공을 의미하지는 않는다.
2. **실적 → 검색결과**에서 클릭수, 노출수, 평균 CTR, 평균 게재순위를 본다. 처음에는 28일을 이전 28일과 비교하고 검색어·페이지·국가·기기별로 나눈다. 평균 순위 하나로 성과를 판단하지 않는다.
3. **색인 생성 → 페이지**에서 색인 제외 이유를 확인한다. **Sitemaps**에 `https://dividendforensics.com/sitemap.xml`을 제출한다. 사이트맵은 발견을 돕지만 색인이나 순위를 보장하지 않는다.
4. **URL 검사**에 홈, 학습 허브, 대표 글, 계산기 URL을 넣어 크롤링 가능 여부와 Google이 선택한 canonical을 확인한다. 모든 URL에 반복적으로 색인 요청을 하는 방식보다 내부 링크와 콘텐츠 품질을 점검한다.
5. **환경 → Core Web Vitals**에서 실제 이용자 성능 데이터를 본다. 트래픽이 적으면 데이터가 없을 수 있다. [PageSpeed Insights](https://pagespeed.web.dev/)에서 개별 URL의 실험실 결과도 확인하되 실제 이용자 지표와 구분한다.

공식 설명: [Search Console 보고서](https://support.google.com/webmasters/answer/9133276?hl=ko), [URL 검사](https://support.google.com/webmasters/answer/9012289?hl=ko), [사이트맵](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

이 작업은 Search Console 계정에 접근하거나 속성·사이트맵 제출을 완료하지 않았다. 사이트 내 가짜 방문수나 SEO 점수를 표시하지 않는다. Search Console은 자연 검색 데이터이며 Benzinga 유입 전체를 측정하는 도구가 아니다.

## Benzinga에서 어떻게 연결할 것인가

발행 플랫폼의 링크 정책을 지키면서 글의 주제와 직접 연결되는 무료 자료로 유도한다. 예를 들어 넷리스 기사에는 `/learn-net-lease.html`, 배당 커버리지 기사에는 `/calculator-payout-ratio.html`, 재융자 기사에는 `/calculator-refinancing.html`을 연결한다. 관련 자료가 독자에게 추가 설명을 제공하도록 짧게 소개하고 같은 본문을 무단 복제하지 않는다.

링크 예시:

`https://dividendforensics.com/learn-net-lease.html?utm_source=benzinga&utm_medium=referral&utm_campaign=reit_education&utm_content=net_lease_explainer`

현재 추적 스크립트가 없기 때문에 UTM을 붙이는 것만으로 유입 보고서가 생기지 않는다. 추후 GA4 또는 다른 분석 도구를 실제로 연결하고 개인정보 고지·필요한 동의 처리를 반영해야 유입과 계산기 사용 이벤트를 집계할 수 있다. Search Console과 분석 도구의 수치는 서로 다른 범위를 측정한다.

## 애드센스 신청과 활성화

1. [AdSense](https://www.google.com/adsense/start/)에 본인 계정으로 신청하고 실제 운영 도메인을 등록한다. 계정의 자격, 결제 정보 등은 소유자가 제공해야 한다.
2. 계정에서 제공하는 사이트 연결·확인 방법과 실제 게시자 ID를 사용한다. 광고 스크립트의 `ca-pub-...`와 ads.txt의 `pub-...` 형식을 구분한다. 예시 ID를 실제 사이트에 배포하지 않는다.
3. 계정이 지시하는 정확한 ads.txt 행을 루트에 추가한다. 루트 ads.txt에는 실제 제공된 ID의 행 `google.com, pub-3030006828946894, DIRECT, f08c47fec0942fa0`를 게시했다. [공식 ads.txt 가이드](https://support.google.com/adsense/answer/12171612?hl=en-EN)를 따른다.
4. 광고를 실제로 활성화하기 전에 개인정보처리방침을 광고·쿠키·제3자 처리에 맞게 수정한다. EEA·영국·스위스 이용자 대상 광고의 경우 [Google 동의 관리 요건](https://support.google.com/adsense/answer/7670013?hl=en)을 확인하고 적절한 Google 인증 CMP를 구성한다. 단순 배너만 넣었다고 요건이 충족되는 것은 아니다.
5. 검토 결과는 AdSense **사이트**에서 확인한다. 승인이나 수익을 보장하지 않는다. [자격 요건](https://support.google.com/adsense/answer/9724?hl=en)과 [사이트 준비 안내](https://support.google.com/adsense/answer/7299563?hl=en)는 원본성·가치·탐색 경험을 강조하며, 이 문서들에 승인 보장용 최소 페이지 수는 없다.
6. 광고 위치는 본문을 가리지 않는 문맥 구분 지점부터 검토한다. 계산 버튼, 메뉴, 입력창 옆에 클릭을 유도하는 광고를 배치하지 않는다. 본인 클릭·클릭 요청·인위적 트래픽을 사용하지 않는다. [광고 게재 정책](https://support.google.com/adsense/answer/1282097?hl=en)을 따른다.

## 콘텐츠 운영

- `content/foundations.json`, `content/sectors.json`, `content/metrics.json`이 신규 교육 글의 원본이다. `education.py`가 본문·관련 글·출처·메타데이터·구조화 데이터를 생성한다. HTML만 직접 수정하면 다음 빌드에서 덮어쓴다.
- 특정 기업의 숫자를 넣을 때 공시일, 대상 기간, 표 위치, 단위, 보통주 귀속 여부와 희석 주식 수를 기록한다. FFO와 AFFO를 현금흐름 또는 법정 배당액과 동일시하지 않는다.
- 제작 도구와 프롬프트 기록은 보관한다. 사용자 방침에 따라 공개 페이지에서 제작 도구를 선제 언급하지 않되, 검토하지 않은 내용을 사람이 검토했다고 주장하거나 플랫폼의 고지 요구에 허위로 답하지 않는다. 운영자가 신규 원고를 읽고 오류·출처·본인 견해를 보완하는 것이 다음 콘텐츠 개선의 핵심이다.
- 페이지를 추가할 때 검색어만 바꾼 유사 글을 늘리지 않는다. 다른 질문, 독립적인 예시, 실제 도움이 되는 공시 읽기 절차를 제공한다. [Google의 유용한 콘텐츠 안내](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)를 기준으로 평가한다.
- 업데이트 날짜는 실제 콘텐츠 변경에 맞춰 관리한다. 오래된 공시를 최신 자료처럼 보이게 하거나 매 빌드마다 날짜만 바꾸지 않는다. 각 글에 별도 업데이트일이 필요해지면 데이터의 날짜 필드를 확장한다.
- `sitemap.xml`은 빌드가 canonical을 기준으로 재생성한다. 리디렉션·404·준비 중 멤버십은 제외한다. 기존 검증 파일과 CNAME은 유지한다.

## 다음 확장 우선순위

1. 실제 공개 공시를 이용한 FFO→AFFO 비교 사례: 정의 차이와 원문 표 위치를 함께 제공.
2. 회사별 유지보수 투자·임차인 개선비·임대 수수료 처리 비교: 단순 종목 순위 대신 조정 기준을 설명.
3. 장기 임대료 인상 조항, sale-leaseback, 리츠 우선주와 조인트벤처 등 독립적인 질문별 심화 글.
4. 검색 실적을 확인한 뒤 수요가 있는 글을 보강. 한국어판은 실제 번역·검수된 별도 URL과 hreflang으로 추가하고 자동 중복 페이지는 만들지 않음.
5. 2027년 멤버십은 사용자 방향성이다. 현재 사이트에는 확정 출시일이나 가격, 결제를 게시하지 않는다. 무료 교육과 유료 연구의 범위를 나중에 별도로 정의한다.

## 검증 명령

```powershell
$env:PYTHONUTF8='1'
python build_site.py
python build_site.py --check
python -m unittest discover -s tests -v
python tools/check_site.py
node --test tests/calculators.test.cjs
```

자동 빌드가 HTML과 사이트맵을 갱신한다. GitHub Pages의 실제 배포 완료는 Actions/Pages 결과와 공개 URL을 확인해야 하며, Git 커밋만으로 배포 성공을 선언하지 않는다.

## 재검수 수정 이후 유지 방법

교육 원고의 `published`는 최초 발행일, `updated`는 실제 내용 수정일로 글별 관리한다. 빌드 실행이나 다른 글 수정 때문에 일괄 갱신하지 않는다. 관련 계산기는 원고의 `calculator` 필드에 정확한 도구 slug를 지정하며, 관련 도구가 없으면 필드를 생략한다. 보고서별 수용·정정·대기 판단은 [재검수 처리 결과](REAUDIT-RESOLUTION-2026-10-18.md)를 참고한다.

- 2026-10-18 디자인 개정: 사용자의 직접 선택에 따라 공개 페이지의 선제 AI 제작 고지는 제거했다. 개념도·가상 예시·기업 실측 자료 아님이라는 설명은 유지하며, 생성 도구와 프롬프트 기록은 `img/education/prompts.json` 및 제작 문서에 보관한다. 플랫폼이 고지를 요구하거나 제작 방식을 묻는 경우 사실대로 대응한다.


## 실제 게시자 ID 연결 — 2026-10-18

확인 방식은 메타 태그다. 홈페이지 head에 `<meta name="google-adsense-account" content="ca-pub-3030006828946894">`가 있다. 사용자가 제공한 스크립트는 광고 활성화 단계와 구분해 아직 삽입하지 않았다. Google이 공식 지원하는 대체 소유권 확인 방식이며 별도 광고 네트워크 요청을 실행하지 않는다.

공개 배포가 확인되면 운영자는 AdSense의 dividendforensics.com에서 **메타 태그**를 선택하고 해당 확인 완료 체크박스·버튼으로 확인한 뒤 **검토 요청**을 진행한다. 또는 **Ads.txt 스니펫** 방식으로 루트 파일을 확인할 수 있다. 현재 선택된 **애드센스 코드 스니펫** 방식으로 확인했다고 표시해서는 안 된다. 계정 내부 클릭·검토 요청은 이 코드 변경으로 실행되지 않는다.

- 확인 파일: https://dividendforensics.com/ads.txt
- 공식 연결 방법: https://support.google.com/adsense/answer/7584263?hl=en
- ads.txt 안내: https://support.google.com/adsense/answer/12171612?hl=en
- 승인/광고 송출·CMP·광고 활성화 후 개인정보 처리 현황은 미확인/미활성 상태다. 사용자 이메일이나 계정 화면은 공개 사이트에 싣지 않는다.


## 검색 질문을 위한 실용 자료 추가 — 2026-10-18

`reit-vs-bdc.html`, `dividend-dates.html`, `dividend-research-worksheet.html`을 추가했다. 기존52개 과정 원고와 별도인 실용 자료3개이며15개 계산 도구 수에 메모 작성기를 섞지 않는다. sitemap.xml 주소는 그대로이고 검색 대상은107개다. 홈·학습실·도구 목록과 관련 입문 글에서 정적 링크로 연결한다. 신규 글마다 자기canonical, Article/Breadcrumb, 실제 발행/수정일, 원출처가 있다.

Search Console 실적의 페이지/검색어 필터로 새 주소의 노출·클릭과 실제 유입 질문을 확인한다. 신설 직후 데이터 부재를 실패로 단정하지 않는다. 언어별/키워드별 검색량은 측정하지 않았으며, 이번 주제 선정은 독자 질문과 기존 콘텐츠 공백에 근거한 가설이다. 기록: `docs/SEO-RESOURCES-2026-10-18.md`.
