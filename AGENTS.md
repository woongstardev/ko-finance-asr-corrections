# AGENTS.md — 에이전트 작업 규칙

이 레포는 껄무새 파이프라인의 교정 자산을 **공개용으로 포장**하는 곳이다.
정본(SSOT)은 껄무새 운영 DB(`correction_dictionary`)이며, 여기 데이터는 필터링된 스냅숏이다.

**작업 시작 전 필독**: [`docs/GGULMUSE-CONTEXT.md`](docs/GGULMUSE-CONTEXT.md) —
상류 관계·방향성·오픈소스 생존 조건·두 레포 협업 규약. 열린 작업은 [`tasks/`](tasks/).

## 하드 라인

- **인물(실명) 쌍을 `data/`에 넣지 않는다.** 종목·금융용어·숫자 쌍만.
- **자막 원문·문맥 예시 문장을 넣지 않는다.** 쌍 + 통계 + 메타만.
- 껄무새 내부 경로·운영 인프라 상세·시크릿을 커밋하지 않는다.
- Tier C(미검증 후보)는 배포하지 않는다.

## 커밋

- 언어: 커밋 메시지 영어, 문서는 파일별 기존 언어 유지 (README·docs = 영어, 이 파일 = 한국어).
- **`docs/SCHEMA.md`를 바꾸는 커밋은 `scripts/validate_snapshot.py`를 같이 바꾼다.** 검증
  규칙이 스키마 문서에서 하드코드로 떨어져 나와 있어(외부 의존 금지) 이중 정본이다 —
  같은 커밋에서 맞추지 않으면 조용히 어긋난다. 검증기의 각 규칙에는 근거가 된 SCHEMA 절이
  주석으로 달려 있다.
- 공개 전까지 스키마 변경 자유. v0.1 이후 `data/` 스키마 변경은 마이너 버전 승격.

## 스냅숏 갱신 (task 005에서 3층으로 자동화 — 2026-08-14)

**주간 감지(자동)**: 유저 타이머가 월요일 07:20에 `refresh_snapshot.py --notify`
**드라이런**을 돌린다 — 재계수(임시 경로, 상류 트리 안 건드림) → export → 게이트 3종 →
현 스냅숏과 diff. 설치·제거는 한 줄이다:

    sh scripts/install-refresh-timer.sh            # 설치 + 즉시 활성화
    sh scripts/install-refresh-timer.sh --remove

리포트는 `OSS_REFRESH_REPORT_DIR`(기본값 `~/.local/state/oss-refresh/reports`, 항상 레포
밖 — 인물 후보가 담긴다). 알림은 `OSS_REFRESH_TELEGRAM_ENV`의 자격증명이 있을 때만 가고,
없으면 경고만 남기고 리포트는 정상 생성된다(알림 배선과 감지를 분리한 것은 의도다 —
배선을 기다리다 감지가 죽어 있는 게 더 나쁘다). 무변화여도 월 1회 하트비트를 보낸다:
침묵과 고장은 달라야 한다.

⚠️ **2026-08-26 현재 텔레그램 자격증명 미배선** — 시크릿 이동이라 웅스타 직접.
그때까지 변화 감지는 리포트 디렉터리를 사람이 열어봐야 보인다.

**월간 발행(사람 개입 1회)**:
1. 주간 리포트의 **새 인물 쌍 후보를 사람이 확인** — 있으면 상류 제외 목록에 추가 후 재실행.
2. `python3 scripts/refresh_snapshot.py --write` — 재계수(정본 아티팩트 갱신 →
   상류에 커밋) → export → **게이트 3종** → `data/` 갱신 +
   `CHANGELOG.md` 반영. 게이트는 후보 export에 대해 돌고, 하나라도 실패하면 쓰지 않는다:
   `release_check.py`(공개 경계) · `validate_snapshot.py`(스키마 계약·인물 최후 방어·
   산문 수치) · `benchmark_gate.py`(평가셋 추가만·연쇄 치환 신규 발생). 드라이런에서는
   같은 게이트가 경고로만 돌고 주간 리포트 머리에 한 줄로 요약된다.
3. `CITATION.cff` version·date 갱신, CHANGELOG의 Unreleased를 버전 절로 승격
4. 릴리스 태그 `vYYYY.MM`
5. (공개 이후에만) HuggingFace 미러 `woongstardev/ko-finance-asr-corrections` push +
   `docs/hf-dataset-card.md`의 버전 문자열 갱신. 공개 전에는 no-op다.

**패치 릴리스(이벤트)**: 배포된 오교정 쌍의 **회수 전용**. 신규 쌍 추가는 패치 사유가 아니다.

인물 제외 목록의 정본 위치는 **상류 `pipeline/data/person-exclusions.txt`**(프라이빗)다 —
목록 자체가 인물 정보라 공개 레포에 두지 않는다. exporter는 상류
목록과 (이관 완료 전까지의) 로컬 레거시 목록의 **합집합**을 쓴다.
