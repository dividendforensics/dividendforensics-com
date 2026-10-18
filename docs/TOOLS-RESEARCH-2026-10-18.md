# REIT·BDC 도구 및 공개 운영 조사

조사일 2026-10-18. 공개 공식 제품 페이지·배포 메타데이터·라이선스·플랫폼 문서만 근거로 사용했다. 로그인·유료 가입·메일 전송·프로필 수정·실제 SEC 수집은 하지 않았다. 제품 기능의 존재를 확인한 것이며 데이터 정확도·유료 서비스 품질·투자성과·DFB보다 우수함을 검증한 것은 아니다.

## 실제 공개 도구와 DFB에 적용할 판단

| 관찰한 공식 공개 제품 | 확인한 기능 | DFB 적용 판단(추론) |
| --- | --- | --- |
| [alreits](https://alreits.com/) | 글로벌 REIT 시장·섹터·스크리너·실적 메뉴와 국가별 개요 | 국가·섹터 탐색을 참고하되 원천 데이터 계약과 조정 정의 없이 시세 스크리너를 복제하지 않는다. 교육용 입력→공식→가정 설명에 집중한다. |
| [REITNotes 발표](https://www.reitnotes.com/announcements/) | FFO·점유율 등 REIT 데이터와 REITAnalytics CSV 내보내기 안내 | 다운로드에는 원시 입력·기간·단위·산식 버전·출처를 함께 제공하는 편이 DFB의 재현성에 맞다. 제품의 CSV나 독점 점수를 재배포할 권한을 뜻하지 않는다. |
| [BDC Investor](https://bdcinvestor.com/) | Price/NAV·배당·baby bonds·스크린·회사별 탐색 | BDC는 REIT FFO 틀에 넣지 않고 NII·PIK·NAV·선언/지급 배당을 구분하는 별도 도구가 필요하다. 순위표를 투자 추천처럼 제공하지 않는다. |

세 사이트는 공개된 독립 제품 사례이지 오픈소스 코드 공급처가 아니다. 공개로 볼 수 있는 데이터·디자인·로고가 자유 재사용 가능하다는 뜻이 아니다. 유료 기능은 구독하거나 검증하지 않았다. 경쟁 제품의 최신 가격이나 정확도를 주장하지 않는다.

## 구현 후보·버전·라이선스

이 조사에서 **파이프라인에 채택한 외부 패키지는 0개**다. Python 3.13.3 표준 라이브러리로 구현하여 Python 공급자 라이선스 범위에서 사용하며 별도 패키지 설치·공개 브라우저 번들 추가가 없다. 아래는 실제 공식 PyPI JSON을 HTTP로 조회한 시점의 버전이며 설치하거나 보안 감사를 통과시킨 버전이 아니다.

| 후보 | 2026-10-18 확인 버전 | 라이선스 근거와 고려사항 | 결정 |
| --- | --- | --- | --- |
| sec-edgar-downloader | `5.1.0`, Python≥3.10 | [PyPI](https://pypi.org/pypi/sec-edgar-downloader/json), [저장소 MIT License](https://github.com/jadchaar/sec-edgar-downloader/blob/master/LICENSE). 재사용/배포 시 저작권·허가 고지 보존 | 현재 메타데이터만 필요해 미채택. 나중에 원문 수집 시 범위·요청량과 의존성을 재검토 |
| edgartools | `5.62.0`, Python≥3.10 | [PyPI](https://pypi.org/pypi/edgartools/json), [MIT License](https://github.com/dgunning/edgartools/blob/main/LICENSE.txt). 회사별 태그와 문서 모델을 사람 검토의 대체로 보지 않음 | 원문/XBRL 확장 시 후보, 현재 미채택 |
| Arelle release | `2.46.1`, Python≥3.10 | [PyPI](https://pypi.org/pypi/arelle-release/json), [Arelle 공식 README·Apache 2.0](https://github.com/Arelle/Arelle). 배포 라이선스/NOTICE와 포함 구성요소 별 조건 검토 필요 | 완전한 XBRL 검증이 필요해질 때 후보. SEC plugin의 버전과 Arelle 본체 버전을 혼동하지 않음 |

PyPI 버전 조회 명령은 각 `https://pypi.org/pypi/{package}/json`에 `Invoke-RestMethod`를 실행하여 `info.version`, `license_expression`, `requires_python`을 읽었다. sec-edgar-downloader의 PyPI license 메타 값은 비어 있어 실제 저장소 LICENSE로 확인했다. 다운로드 아티팩트의 버전별 라이선스·전체 전이 의존성과 취약점은 설치 결정 시 lockfile+해시+스캔으로 추가 검증해야 한다. 현재 미채택 후보의 미래 버전까지 허가했다고 주장하지 않는다.

GPL은 상업 이용이 원천 금지된 라이선스가 아니다. FSF는 유료 판매를 허용한다고 설명한다. 배포 형태에 따른 소스 제공·동일 라이선스 등 조건을 검토해야 하며, MIT/Apache도 고지 의무가 있다. 그러므로 “상업 사이트이므로 GPL 전부 금지”나 “오픈소스이므로 무조건 복사 가능” 모두 부정확하다. [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#DoesTheGPLAllowMoney), [GPLv3 원문](https://www.gnu.org/licenses/gpl.en.html).

## SEC 입력과 데이터 경계

SEC 공개 submissions API는 인증키 없이 사용하며 CORS를 지원하지 않는다. 요청을 브라우저 방문자에게 분산해서 보내지 않는다. 식별 가능한 운영 연락처가 있는 User-Agent와 캐시를 사용한다. SEC는 여러 장비를 합친 사용자당 초당 10회 이하를 안내한다. 현재 도구는 단일 호스트 공용 gate로 초당 1회 이하를 적용하며 403/429에서 중단·backoff한다. [SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC Developer Resources](https://www.sec.gov/about/developer-resources).

API에 공시가 존재하는 사실은 그 접수의 모든 조정 지표·주석 수치를 표준화했다는 뜻이 아니다. Company Facts에서 회사 고유의 JV·PIK·임대 만기 표를 모두 얻을 수 있다고 가정하지 않는다. 기업별 정의, 연결 범위, 총액/주당, 통화·배율과 기간을 보존하고 원문을 수동 검토한다. 구현·운영·미실행 범위는 [FILING-REVIEW.md](FILING-REVIEW.md)에 기록했다.

## 저자 프로필 활용

[Benzinga 저자 페이지](https://www.benzinga.com/author/jeong-mo-goo)와 공개 기사의 byline은 `Jeong-Mo Goo`와 `Benzinga Contributor`를 뒷받침한다. [Muck Rack 프로필](https://muckrack.com/jeong-mo-goo)도 해당 이름과 기고 이력을 연결한다. 이 사실은 Benzinga 정규 고용·플랫폼의 검증/보증·투자자문 자격·CFA·CPA를 입증하지 않는다. Muck Rack의 프로필 분류 문구를 자격증처럼 옮기지 않는다.

권장 연결은 실제 canonical 저자 페이지의 `Person`과 동일한 이름·안정적인 `@id`, 두 실제 프로필 `sameAs`, 기사별 실제 출처/날짜다. 프로필의 글 수를 독립 감사한 발행 수로 표현하거나 새 게시물이 있다고 추정해 아카이브에 자동 추가하지 않는다. 외부 403·도구 timeout은 링크 부재의 증거가 아니다. 계정·프로필 수정 또는 매체에 연락하지 않았다.

이번 조회에서 Muck Rack과 [Benzinga ARI 뉴스 목록](https://www.benzinga.com/quote/ARI/news)은 2026-09-30 ARI 청산 기사와 Jeong-Mo Goo byline을 보여 준다. 이는 종전 09-25까지의 제한된 검색보다 넓은 **추가 발견**이다. 아카이브에 넣으려면 실제 개별 기사 URL과 날짜를 다시 검증해야 하며, 본 조사 도구가 자동으로 저장소 게시 목록을 수정하지는 않았다.

## 실제 호스팅과 AdSense 준비

GitHub Pages 약관은 온라인 사업·전자상거래 또는 주로 상업 거래/SaaS 제공을 위한 무료 호스팅으로 사용하는 것을 제한한다. 이는 모든 교육 페이지의 광고를 명시적으로 일괄 승인한다는 규정도, 광고가 하나라도 있으면 무조건 금지한다는 규정도 아니다. **추론:** 광고 수익과 유료 의뢰가 주목적이 되는 단계에는 GitHub의 현재 허용 범위를 확인하거나 상업 이용에 맞는 호스팅으로 이전하는 편이 운영상 명확하다. 결제·계정 정보를 Pages에 수집하지 않는다. [GitHub Pages 제한](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

대안을 고를 때 무료 요금제라는 이유만으로 상업 이용을 가정하지 않는다. 예컨대 Vercel Hobby는 공식 문서에서 개인 비상업 용도를 명시한다. Cloudflare Pages 공식 문서는 정적 배포·제한을 제공하지만 이것만으로 모든 사업의 약관 적합성을 보증하지 않는다. 실제 선택은 현재 약관·사용량·도메인·redirect·정책을 확인한 뒤 별도 작업으로 한다. 이 조사에서 계정 생성·호스팅 이전·DNS 변경은 하지 않았다. [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Cloudflare Pages](https://developers.cloudflare.com/pages/), [Cloudflare 제한](https://developers.cloudflare.com/pages/platform/limits/).

Google은 자체 원본 콘텐츠·정책 준수·사이트 관리 권한·신청자 요건을 요구한다. 특정 글 수·계산기 수·오픈소스 사용·작동하는 도메인은 승인을 보장하지 않는다. 실제 AdSense 계정·게시자 ID·소유권/개인정보·광고 배치는 별도 확인이 필요하다. [AdSense 자격](https://support.google.com/adsense/answer/9724). 이 단계는 ID 발급·광고 송출·CMP·Search Console 확인 또는 수익 발생을 수행한 것이 아니다.

## 조사 범위와 결과

- PASS: 위 공식 공개 제품/프로필/SEC/호스팅/라이선스 문서 조회 및 PyPI 후보 버전 조회.
- PASS: 메타데이터 전용 수동 pipeline과 합성 fixture 검증은 별도 운영 문서에 기록.
- NOT RUN: 유료 서비스 내부 평가, 후보 패키지 설치·전체 의존성/취약점 감사, 실제 SEC 수집·원문 수치 대조, AdSense 신청·메일 송수신·스케줄·호스팅 이전.
- 다음 결정: 실제 CIK와 User-Agent, 검토 담당자, 상업 운영 호스팅 적합성, 승인 snapshot의 별도 게시 정책. 미정 항목을 실제로 완료한 것처럼 표시하지 않는다.
