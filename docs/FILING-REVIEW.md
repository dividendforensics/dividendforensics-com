# SEC 수동 공시 검토 도구

기준일: 2026-10-18. 구현 버전 `scripts/filing_review.py`의 `1.0.0`. Python 표준 라이브러리만 사용한다. **수동 CLI 도구이며 자동 게시·일정·이메일 기능은 없다.** 실제 SEC 실행과 실제 사람의 공시 검토는 아직 실행하지 않았다.

## 실제 구현 범위

검증한 CIK 허용 목록 → SEC submissions의 `recent` 메타데이터 → 중복 없는 `needs_review` 후보 → 운영자가 직접 제공한 승인/반려 기록 → 별도 명령의 비공개 snapshot 내보내기다. 10-K·10-Q·8-K와 `/A`만 지원하며 회사별로 서식을 명시한다. 모든 8-K를 실적 공시라고 분류하지 않는다.

원문·첨부·Company Facts를 다운로드하거나 수치를 추출하지 않는다. 후보의 `primary_document_fetched=false`, `metrics=null`이 이를 표시한다. `needs_review`는 메타데이터 후보 상태일 뿐 원문을 검토했다는 주장이 아니다. `related_accessions`도 같은 CIK·보고기간·기본 서식의 **관련 가능성**이며 수정본이 특정 수치를 대체했다는 뜻이 아니다.

공개 빌더는 이 도구나 대기열을 읽지 않는다. 캐시·상태·승인 기록·내보낸 snapshot은 GitHub Pages로 서비스되는 저장소 **밖**에만 저장할 수 있다. 승인하더라도 공개 페이지·사이트맵·계산기 기본값은 바뀌지 않는다. 이 단계에 `published`로 바꾸는 기능은 없다.

## 준비

실제 운영자 연락처가 포함된 User-Agent와 검증된 CIK를 소유자가 준비한다. 기본 예시의 `companies`는 비어 있으며 실제 회사나 검토자 이름을 가정하지 않는다. `data/filing-watchlist.example.json`을 저장소 밖에 복사하고 `declaredUserAgent`를 실제 값으로 바꾼다.

```json
{
  "declaredUserAgent": "실제 조직/응용프로그램 이름 실제-연락처-이메일",
  "companies": []
}
```

회사 항목 필드: `cik`(선행 0을 포함한 정확한 10자리 문자열), `name`, `verificationSource`(CIK를 확인한 공식 출처 기록), `forms`(예: `["10-Q", "10-Q/A", "8-K"]`), `enabled`(명시적 boolean). 공개 예시에는 실제 회사를 넣지 않았다. 티커로 CIK를 추정하지 않는다.

## 수동 명령

아래 PowerShell 경로는 예시다. 먼저 실제 설정 파일과 대상 기간을 정한다. 명령은 저장소 루트에서 실행한다.

```powershell
python scripts/filing_review.py --help
python scripts/filing_review.py --config C:\DFB-private\watchlist.json --state-dir C:\DFB-private\state collect --since 2026-09-01
python scripts/filing_review.py --config C:\DFB-private\watchlist.json --state-dir C:\DFB-private\state collect --since 2026-09-01 --cache-only --max-cache-age 86400
python scripts/filing_review.py --config C:\DFB-private\watchlist.json --state-dir C:\DFB-private\state review --key 0000000001:0000000001-26-000001 --decision approved --record C:\DFB-private\manual-review.json
python scripts/filing_review.py --config C:\DFB-private\watchlist.json --state-dir C:\DFB-private\state export --output C:\DFB-private\exports\approved-snapshot.json
```

위 승인 명령의 CIK/accession은 **합성 예시**이며 실제 데이터가 아니다. 반려에는 `--decision review_rejected`를 사용한다. 실제 승인 기록 없이 명령만 실행하면 실패한다. `failed`·`partial_failure` 수집은 종료 코드 2이며, 검증 실패는 오류로 종료한다.

`--since`는 사용자가 선택하는 겹치는 접수일 구간이다. 최초 실행은 `baseline`으로 표시하여 과거 자료를 새 알림처럼 다루지 않는다. 별도 알림 기능 자체가 없다. 이후에도 마지막 실행일 이후만 조회하지 말고 겹치는 구간을 사용한다. 현재는 `recent`만 읽으므로 장기 과거 접수를 전수 수집하지 않는다. SEC가 `filings.files`에 과거 파일을 제공하면 `historical_files_not_fetched=true`를 남긴다. 큰 과거 구간을 지정해도 완전 수집이라고 주장하면 안 된다.

## 검토 기록

실제 사람이 원문을 열어 확인한 후 자신의 이름·실제 검토 시각·의견을 직접 입력한다. 도구는 신원 인증이나 검토 사실의 독립 검증을 수행하지 않는다. 모든 기록에는 `operator_supplied_manual_record; not independent verification` 출처가 남는다. 수집 명령이 검토자 이름·검토 시각·승인 값을 만들어 주지 않는다.

승인 기록은 다음 구조다. 아래는 형식 설명용 합성 fixture이며 승인 템플릿을 실제 검토처럼 제출하면 안 된다.

```json
{
  "reviewer": "실제 검토자",
  "reviewed_at": "실제 시간대 포함 ISO 시각",
  "notes": "확인 범위와 정의 차이, 미해결 문제",
  "fields": [{
    "name": "reported_nii",
    "value": null,
    "missing_reason": "해당 자료에서 확인하지 못함",
    "source_url": "해당 accession 경로 아래 https://www.sec.gov/Archives/... 원문",
    "document_location": "문서명·표·페이지 또는 주석 위치",
    "period": "원문의 보고기간",
    "unit": "million 또는 per common share 등 원문 배율",
    "currency": "USD 등 원문 통화",
    "basis": "reported/adjusted·선언/지급 등 정확한 기준",
    "input_method": "manual"
  }]
}
```

실제 값은 `"120.50"`과 같은 **10진수 문자열**로만 기록한다. 0은 `"0"`, 미확인은 `null`과 `missing_reason`이며 서로 다르다. 숫자형 JSON·NaN·Infinity·쉼표·지수 표기·자동 형변환을 허용하지 않는다. 통화·기간·배율을 기록하지만 이 도구는 서로 다른 필드를 자동으로 합산하거나 배당성향을 계산하지 않는다. 따라서 승인 기록을 계산기나 실제 사례로 옮기기 전 기간·정의·범위·단위 일치 검토가 별도로 필요하다.

같은 후보에 여러 검토 기록을 남길 수 있고 과거 사건은 보존한다. 최신 결정이 반려이면 이후 내보내기에서 해당 후보를 제외한다. 승인 기록이 하나도 없으면 기존 snapshot을 지우거나 빈 파일로 교체하지 않는다. 이전에 내보낸 snapshot을 자동 삭제하지도 않으므로 **내보내기 날짜와 최신 반려 기록을 함께 확인**해야 한다. snapshot 자체는 게시 완료나 최신 상태의 인증이 아니다.

## 오류·잠금·캐시

- `(CIK, accession)`을 키로 중복 제거한다. 같은 기간의 여러 접수와 `/A`는 별도로 보존한다. 같은 accession의 주요 메타데이터가 달라지면 오류로 남기며 기존 값을 조용히 덮어쓰지 않는다.
- 수집 성공 JSON의 CIK·필수 배열·동일 배열 길이·접수번호·날짜·원문 파일명을 검증한 뒤 캐시를 교체한다. 403·429·timeout·잘린 JSON·구조 오류는 0건 성공이 아니다.
- `state.json`에는 후보·검토 사건·실행 기록·마지막 **전체 신선 수집 성공** 시각이 있다. 부분 실패와 캐시 읽기는 마지막 전체 성공 시각을 올리지 않는다. 한 회사 실패가 다른 회사나 과거 후보를 지우지 않는다. 실패 건에는 `found:0`을 만들지 않는다.
- 원자적 임시 파일 작성·fsync·`os.replace`를 사용한다. 캐시와 상태는 개별 원자적 파일이며 둘을 아우르는 데이터베이스 트랜잭션은 아니다. 중단 후 accession 중복 제거로 재실행한다. 승인 snapshot은 별도 명시적 내보내기에서만 원자적으로 바뀐다.
- 상태 경로의 `run.lock`으로 실행과 승인/내보내기를 직렬화한다. 기본 `~/.dfb-sec-gate`의 공용 잠금과 타이머가 **같은 컴퓨터·같은 사용자**의 여러 상태 경로 요청을 합쳐 요청 시작 간격을 최소 1초로 제한한다. 잠금 경합은 요청을 우회하지 않고 실패한다. 여러 컴퓨터·사용자 계정·다른 SEC 프로그램까지 분산 제어한다고 주장하지 않는다. 운영자는 단일 수집 호스트를 사용하고 다른 도구 사용량도 SEC 사용자별 총량에 포함해야 한다.
- 403/429는 전체 실행의 나머지 회사 요청을 중단한다. 숫자 또는 HTTP-date `Retry-After`를 읽어 최소 60초의 다음 요청 시각을 보존하며, 해석할 수 없으면 900초 backoff다. IP·호스트·User-Agent 교체 우회나 자동 연속 재시도는 없다. 다음 수동 실행은 남은 대기 시간을 기다릴 수 있다.
- 강제 중단으로 잠금이 남으면 해당 디렉터리 `owner.json`의 PID와 실제 프로세스를 확인한 뒤 운영자가 직접 제거한다. 자동으로 잠금을 훔치지 않는다.
- 캐시 재사용은 `--cache-only`로만 명시하며 원본 성공 시각·해시와 오래됨 표시가 남는다. 자동 실패 후 오래된 캐시를 신선 데이터처럼 대체하지 않는다.
- 네트워크는 고정 `data.sec.gov/submissions/CIK##########.json` HTTPS 주소만 사용하고 redirect·임의 URL·localhost·내부 IP를 요청하지 않는다. 30초 timeout·10MiB 응답 제한이 있다. 공시 문자열을 코드·셸·프롬프트 지시로 실행하지 않고 첨부를 열지 않는다. 로그에는 외부 오류 본문·UA·메일 전문·토큰을 출력하지 않는다. 수동 notes에 비밀 정보를 넣지 않아야 한다.

SEC의 공개 API는 키 없이 사용할 수 있으며 브라우저 CORS를 지원하지 않는다. SEC 사용자별 상한은 장비 합계 초당 10회이고, 여기의 1회/초는 자체 보수적 운영값이다. [SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [공정 접근 지침](https://www.sec.gov/about/developer-resources).

## 실행한 검증과 미실행

2026-10-18, Windows·Python 3.13.3에서 다음 명령 실행:

```powershell
python -m unittest discover -s tests -p test_filing_review.py -v
```

**PASS: 32개 합성 fixture/mock 테스트 및 `python scripts/filing_review.py --help`.** CIK·allowlist·중복·수정본·충돌·403/429/timeout/잘린 JSON·부분 실패·마지막 성공/승인 snapshot 보존·서로 다른 상태 경로의 공용 rate gate·별도 프로세스 잠금·캐시 시각·원자적 쓰기 실패·검토 필수 필드·null/0 구분·비허용 URL·명시적 export를 검증했다. 실제 회사 수치를 검증한 결과가 아니다.

**NOT RUN:** 실제 SEC 네트워크 수집(실제 CIK와 연락처 미확정), 실제 공시 원문 수치 추출/사람 검토, 여러 컴퓨터 분산 제한, 이메일 수신/발송, cron, 자동 공개, 실제 사람의 화면낭독기 검수. 이메일·일정·공개 연결은 구현하지 않았으며 활성화하지 않았다. 전체 프로젝트 브라우저/회귀·배포 검증은 별도 상위 작업 기록을 참조한다.

## 다음 AI에게 전달할 질문

1. 이 메타데이터 전용 단계의 `needs_review` 표시가 원문 검토와 혼동되지 않는가?
2. 실제 CIK와 연락처를 설정한 뒤 단일 호스트의 제한된 수동 실행에서 SEC 접근·cache·backoff가 정상인가?
3. 이후 원문 추출을 추가한다면 기간·통화·배율·NII/PIK 정의·연결 JV 중복 검사를 어떤 필드 계약으로 표현할 것인가?
4. 여러 수집 컴퓨터가 필요해질 경우 사용자별 합산 제한을 위해 중앙 작업 큐·분산 lock을 어떻게 도입할 것인가?
5. 공개 snapshot 통합은 별도 명시적 검토/게시 단계로 유지하고, 반려·철회 후 기존 공개 버전을 어떻게 정정할 것인가?

추천 방어적 ignore: `.filing-review*/`, `.dfb-sec-gate/`, `**/__pycache__/`. 현재 기본 상태·캐시·검토 파일은 저장소 밖에 두므로 이 ignore만으로 비공개를 보장한다고 주장하지 않는다.
