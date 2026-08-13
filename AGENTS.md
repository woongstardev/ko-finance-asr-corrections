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
- 공개 전까지 스키마 변경 자유. v0.1 이후 `data/` 스키마 변경은 마이너 버전 승격.

## 스냅숏 갱신 (task 005에서 3층으로 자동화 — 2026-08-14)

**주간 감지(자동, 사람 개입 없음)**: 오르빗 유저 타이머 `oss-corrections-refresh.timer`
(월 07:20 KST)가 `scripts/refresh_snapshot.py --notify` **드라이런**을 돌린다 —
재계수(임시 경로, 상류 트리 안 건드림) → export → 현 스냅숏과 diff.
리포트는 `$OSS_REFRESH_REPORT_DIR/`(인물 후보가 담기므로 레포 밖), 변화·실패 시에만
텔레그램 알림(무변화여도 월 1회 하트비트 — 침묵과 고장을 구분한다).

**월간 발행(사람 개입 1회)**:
1. 주간 리포트의 **새 인물 쌍 후보를 사람이 확인** — 있으면 상류 제외 목록에 추가 후 재실행.
2. `python3 scripts/refresh_snapshot.py --write` — 재계수(정본 아티팩트 갱신 →
   껄무새에 an upstream pipeline task 명의로 커밋) → export → `data/` 갱신 + `CHANGELOG.md` 반영.
   내부에서 `scripts/release_check.py`(공개 경계 검사)가 먼저 돌고, 실패하면 쓰지 않는다.
3. `CITATION.cff` version·date 갱신, CHANGELOG의 Unreleased를 버전 절로 승격
4. 릴리스 태그 `vYYYY.MM`

**패치 릴리스(이벤트)**: 배포된 오교정 쌍의 **회수 전용**. 신규 쌍 추가는 패치 사유가 아니다.

인물 제외 목록의 정본 위치는 **상류 `pipeline/data/person-exclusions.txt`**(프라이빗)다 —
목록 자체가 인물 정보라 공개 레포에 두지 않는다(껄무새 an upstream pipeline task). exporter는 상류
목록과 (이관 완료 전까지의) 로컬 레거시 목록의 **합집합**을 쓴다.
