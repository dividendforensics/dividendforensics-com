# SEO 노출 준비와 실제 측정

기준일 2026-10-18. 이 문서는 **검색엔진이 읽을 수 있는 정적 구현 검사**와 **Google 계정에서 확인해야 하는 노출 결과**를 구분한다. 현재 작업에서 Search Console 계정·색인 현황·검색 순위·실제 검색량에 접근하지 않았다. 사이트맵이나 구조화 데이터 검사가 통과해도 Google 색인·노출·트래픽·AdSense 승인을 보장하지 않는다.

## 이번에 확인한 정적 결과

실제 `build_site.planned_outputs`를 읽는 `tools/seo_audit.py`를 실행했다. 생성 HTML이 아직 디스크에 다시 저장되지 않은 상황을 오래된 페이지 오류로 오인하지 않도록 기본 검사는 다음 빌드의 HTML과 사이트맵을 함께 사용한다. 운영 서버의 응답·Google이 선택한 canonical·실제 크롤링 성공을 검사한 것은 아니다. 아래 97개는 **스페인어 추가 전 영어판 검사 시점**의 수치다. 도구는 페이지 수를 고정하지 않고 `es/` 등 하위 경로도 보존하며, 번역이 통합된 뒤 다시 실행하여 새 수치를 기록해야 한다.

| 항목 | 로컬 계획 빌드 검사 결과 |
| --- | --- |
| 색인 허용 정적 canonical 페이지 | 97개 |
| 사이트맵 URL | 97개, 위 canonical 집합과 일치 |
| 제목·description·canonical·H1 | 각 페이지에 1개씩 존재, 중복 없음 |
| 내부 탐색 | 97개 모두 홈에서 정적 `a[href]`를 따라 도달 가능; 홈 외 페이지에 다른 색인 허용 페이지의 내부 유입 링크 존재 |
| BDC 원고 | 16개 모두 Article 제목·대표 URL·발행/수정일이 `content/bdc.json`과 일치, US BDC 범위 문구 확인 |
| 실제 기록 기반 `lastmod` | Article의 `dateModified`와 일치하는 54개. 빌드 실행일을 수정일로 넣지 않음 |
| 중요한 오류 | 0개 |
| 참고 경고 | 2개. BDC credit-memo 제목 86자, Research Desk description 214자. 길이만으로 오류나 순위 하락이라고 판단하지 않음 |

제외된 활성 페이지 12개는 `404.html`, `membership.html`, `breakbefore.html`와 9개 `case-*` 출처 안내 페이지다. 이들은 `noindex,follow` 또는 해당 제외 목적을 유지하며 사이트맵에 포함하지 않는다. 레거시 redirect와 Google 소유권 확인 파일은 콘텐츠 페이지 수와 별도로 취급한다. 소유권 확인 파일이 존재한다는 것만으로 Search Console 소유권 인증이 완료됐다고 주장하지 않는다.

```powershell
python tools/seo_audit.py --output .qa/seo-audit.json
python -m unittest discover -s tests -p test_seo.py -v
```

위 실행 결과: **정적 감사 PASS, SEO 회귀 테스트 16개 PASS**. 하위 경로·스페인어 lang·상호 hreflang·self canonical·영어 x-default 검사가 포함된다. 선택적 JSON 보고서는 로컬 `.qa` 안에만 생성하도록 제한한다. 저장된 배포용 파일을 별도로 확인하려면 빌드를 저장한 뒤 다음을 실행한다.

```powershell
python build_site.py
python tools/seo_audit.py --saved-files --output .qa/seo-audit-saved.json
```

`--saved-files`는 저장 파일 검사이며 웹 서버를 요청하지 않는다. 해당 선택 명령의 통과 여부는 실제로 실행한 이후에만 별도 기록한다. 현재 기본 보고서는 `input: planned_outputs`로 범위를 표시한다.

## 검색 의도와 대표 페이지

다음은 콘텐츠의 질문에 맞춘 **편집상 타깃 예시**다. 실제 검색 수요·경쟁도·순위가 확인된 키워드 목록이 아니며, 이 문구를 반복해 넣거나 같은 질문의 얇은 페이지를 추가하라는 뜻도 아니다.

| 사용자가 해결할 질문 | 우선 대표 페이지 | 이어 읽거나 실행할 곳 |
| --- | --- | --- |
| What is a BDC? | [BDC 구조와 주주의 청구권](https://dividendforensics.com/learn-bdc-basics.html) | [BDC 초급 경로](https://dividendforensics.com/course-bdc-beginner.html) |
| BDC NII dividend coverage | [NII와 분배금 커버리지](https://dividendforensics.com/learn-bdc-nii-coverage.html) | [NII·PIK 워크시트](https://dividendforensics.com/calculator-bdc-nii-pik.html) |
| What is PIK income in a BDC? | [PIK 계약·회계·현금의 차이](https://dividendforensics.com/learn-bdc-pik-income.html) | [PIK 비율 도구](https://dividendforensics.com/calculator-bdc-pik-ratios.html) |
| BDC NAV discount calculator | [BDC 가격/NAV 계산기](https://dividendforensics.com/calculator-bdc-nav-discount.html) | [할인과 기대수익 구분](https://dividendforensics.com/learn-bdc-nav-discounts.html) |
| REIT FFO versus AFFO | [AFFO 정의와 조정 비교](https://dividendforensics.com/learn-affo.html) | [FFO 설명](https://dividendforensics.com/learn-ffo.html) |
| REIT dividend income calculator | [배당 수입 계산기](https://dividendforensics.com/calculator-dividend-income.html) | [배당수익률과 총수익](https://dividendforensics.com/learn-yield-total-return.html) |

기존 REIT 경로와 신규 BDC 경로는 구별한다. BDC 원고에 REIT FFO/AFFO 정의를 복사하거나 동일한 검색 질문에 사실상 같은 글을 여러 URL로 만들어 노출을 늘리려 하지 않는다. 검색 사용자의 질문, 독립적인 예제와 원문 출처가 각 페이지의 가치를 결정해야 한다.

## 운영자가 Search Console에서 실제로 확인할 곳

1. **소유권 확인:** 실제 Google 계정에서 `dividendforensics.com` 속성을 확인한다. Domain 속성은 DNS 확인을 사용한다. 기존 HTML 확인 파일은 URL-prefix 속성의 별도 방법이며 Domain 속성 DNS의 대안이 아니다. 현재 계정의 소유권 상태를 이 작업에서 확인하지 않았다. [Google 소유권 확인 안내](https://support.google.com/webmasters/answer/9008080).
2. **사이트맵 제출:** 소유권이 확인된 속성의 Sitemaps에서 `https://dividendforensics.com/sitemap.xml`을 제출하고 최근 읽은 시각·처리 결과를 확인한다. 제출 성공은 모든 URL의 색인 완료가 아니다. URL 목록은 선호 canonical을 제공하는 신호이며 실제 선택은 Google이 한다. [Google 사이트맵 제출·정확한 lastmod 안내](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).
3. **대표 URL 검사:** 홈, `learn-bdc.html`, BDC 기초·PIK·전문가 메모, REIT AFFO, 대표 계산기를 URL Inspection으로 확인한다. 색인된 버전과 현재 라이브 테스트를 구분하고, 크롤링 허용·가져오기 성공·사용자 지정 canonical·Google 선택 canonical을 비교한다. [URL Inspection 안내](https://support.google.com/webmasters/answer/9012289).
4. **Page indexing:** 제외 원인과 예시 URL을 읽는다. 의도된 `noindex`·redirect·404를 색인 허용 페이지의 문제와 혼동하지 않는다. 발견됨/크롤링됨이나 라이브 테스트 성공만으로 실제 검색 노출을 주장하지 않는다. [Page indexing 보고서](https://support.google.com/webmasters/answer/7440203).
5. **Performance → Search results:** 실제 자료가 쌓이면 같은 기간과 검색 유형을 기준으로 Queries·Pages·Countries·Devices를 분리해 본다. 각 질문/페이지의 impressions, clicks, CTR, average position을 함께 확인하고 데이터가 적은 표본의 순위를 단정하지 않는다. BDC와 REIT URL 경로를 필터링하면 독자의 질문 차이를 비교하기 쉽다. 개인정보 보호와 집계 때문에 모든 검색어가 개별 행으로 제공되는 것은 아니다. [Performance 보고서](https://support.google.com/webmasters/answer/7576553).

조회 결과는 확인 날짜·속성·URL·보고 기간·실제 상태와 함께 기록한다. 아직 접근하지 않은 계정 상태를 ‘정상’, ‘색인 완료’, ‘순위 상승’으로 채우지 않는다. Search Console 데이터는 Google 검색 노출·클릭을 보며, Benzinga 같은 외부 매체의 추천 유입을 전체적으로 측정하는 대체 수단은 아니다. UTM 문자열만 붙여서는 자체 방문 분석이 만들어지지 않는다.

## 구현 판단의 공식 근거와 한계

- 고유하고 내용을 설명하는 제목을 유지한다. Google은 여러 정보를 사용해 결과 제목을 만들며, 고정 60자 제한 같은 합격선을 제시하지 않는다. 긴 제목의 표시 폭이나 중복·키워드 나열을 검토하되 의미 있는 수업 제목을 무조건 잘라내지 않는다. [제목 링크 지침](https://developers.google.com/search/docs/appearance/title-link).
- 주요 이동은 정적 HTML의 정상적인 `a` 요소와 `href`로 제공한다. JS 필터·퀴즈·계산기 동작과 별개로 본문과 연결을 읽을 수 있게 한다. 감사 도구는 script 안의 이동 문자열이나 자기 자신으로 향하는 링크만으로 고아 페이지 문제가 해결됐다고 계산하지 않는다. [크롤링 가능한 링크 지침](https://developers.google.com/search/docs/crawling-indexing/links-crawlable).
- 사이트맵은 색인을 원하는 canonical만 포함한다. `lastmod`는 중요한 실제 수정과 일치해야 하며 매번 빌드 날짜로 올리지 않는다. 기록이 없는 정책·허브 페이지에 오늘 날짜를 만들어 넣지 않는다. [사이트맵 지침](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

이 감사는 문자열·메타데이터·정적 링크 그래프·JSON-LD·소스 날짜의 정합성 검사다. Google의 렌더링·색인 판단, 서버 헤더·차단·응답 속도, 코어 웹 바이탈, 모든 외부 출처의 생존, 실제 사용자의 접근성 또는 금융 내용의 전수 정확성을 판정하는 검사가 아니다. 그러한 결과는 각각 실제 실행 범위를 별도로 기록한다.


## 스페인어 초기판과 측정 범위

이후 스페인어 핵심판7페이지를 추가했다: `/es/`와 입문 글4편, USD 배당 수입·AFFO 스트레스 계산기2개. 영어 원문 주소는 유지하고 각 페이지는 자기 언어의 canonical을 사용한다. 대응하는7쌍에는 en/es 상호 hreflang과 영어 x-default를 넣는다. 없는 번역으로 자동 이동시키거나 전체52편이 번역됐다고 표시하지 않는다.

스페인어 우선·브라질 포르투갈어 다음이라는 순서는 사용자가 선택한 초기 가설이다. 언어별 미국 REIT/BDC 검색량 순위를 측정한 결과로 주장하지 않는다. B3의 FII 투자자 수는 미국 REIT나 BDC 검색량이 아니다. 다음 언어의 착수 전 Search Console에서 `/es/` 페이지 필터와 실제 검색어·국가·노출·클릭·CTR을 본다. 국가는 언어와 동일하지 않으며 절대 검색량을 Search Console의 자사 노출수로 대체하지 않는다. 체류·읽기 정도는 현재 연동되지 않은 분석 도구로 측정했다고 주장하지 않는다.

스페인어 통합 후 계획·저장 HTML SEO 감사:104개 색인 대상=104개 사이트맵 URL,16개 BDC 원고 스키마, 오류0. 언어 페이지·공개 배포·최종 실행 기록은 BDC 확장 릴리스 문서에 갱신한다. 계정 로그인·색인 요청은 미실행이다.
