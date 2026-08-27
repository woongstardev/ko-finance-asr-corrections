# Changelog

All notable changes to the published snapshot (`data/`) are recorded here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), adapted for a
dataset — **Added** = new pairs, **Removed** = pairs recalled from the snapshot
(the only patch-release trigger), **Changed** = metadata changes on existing
pairs (tier, evidence, scope — not weekly frequency drift, which is expected as
the corpus grows and is not chronicled per-pair).

Versions are calendar snapshots (`vYYYY.MM`) after the initial `v0.1`; a pair's
identity across versions is its `(wrong, right)` tuple (`docs/SCHEMA.md`).
Entries are appended by `scripts/refresh_snapshot.py --write`; the Unreleased
section becomes the next release's notes.

## [Unreleased]

### Changed
- `AMAMD → AMD`: ticker, market (2026-08-27)
- `AM대 → AMD`: ticker, market (2026-08-27)
- `IS% → ISC`: ticker, market (2026-08-27)
- `MDI → 엔비디아`: ticker, market (2026-08-27)
- `M비디아 → 엔비디아`: ticker, market (2026-08-27)
- `SK 하이네스 → SK 하이닉스`: ticker, market (2026-08-27)
- `SK 하이스 → SK하이닉스`: ticker, market (2026-08-27)
- `SK 하이하스 → SK하이닉스`: ticker, market (2026-08-27)
- `SK 하인 → SK하이닉스`: ticker, market (2026-08-27)
- `SKS → SK하이닉스`: ticker, market (2026-08-27)
- `SK니스 → SK하이닉스`: ticker, market (2026-08-27)
- `SK닉스 → SK하이닉스`: ticker, market (2026-08-27)
- `SK하닉스 → SK하이닉스`: ticker, market (2026-08-27)
- `SK하잉 → SK하이닉스`: ticker, market (2026-08-27)
- `SMP → 에스앤피`: ticker, market (2026-08-27)
- `S아닉스 → SK하이닉스`: ticker, market (2026-08-27)
- `XAI → xAI`: ticker, market (2026-08-27)
- `김에비디아 → 엔비디아`: ticker, market (2026-08-27)
- `나마토건 → 남화토건`: ticker, market (2026-08-27)
- `남마토건 → 남화토건`: ticker, market (2026-08-27)
- `남마토원 → 남화토건`: ticker, market (2026-08-27)
- `남화통원 → 남화토건`: ticker, market (2026-08-27)
- `대원전설 → 대원전선`: ticker, market (2026-08-27)
- `라이언 라이엇 → 라이엇`: ticker, market (2026-08-27)
- `마이러크럼 → 마이크론`: ticker, market (2026-08-27)
- `마이크로님 → 마이크론`: ticker, market (2026-08-27)
- `브드컴 → 브로드컴`: ticker, market (2026-08-27)
- `비슷하라 → 비스타라`: ticker, market (2026-08-27)
- `삼성근자 → 삼성전자`: ticker, market (2026-08-27)
- `삼성원자 → 삼성전자`: ticker, market (2026-08-27)
- `삼성자 → 삼성전자`: ticker, market (2026-08-27)
- `삼성전나 → 삼성전자`: ticker, market (2026-08-27)
- `삼성제카인 → 삼성전자`: ticker, market (2026-08-27)
- `셀트리오 → 셀트리온`: ticker, market (2026-08-27)
- `스페이스섹스 → 스페이스X`: ticker, market (2026-08-27)
- `스페이스엑스 → 스페이스X`: ticker, market (2026-08-27)
- `신형증권 → 신영증권`: ticker, market (2026-08-27)
- `아모래 퍼시픽 → 아모레퍼시픽`: ticker, market (2026-08-27)
- `아이비 → IBM`: ticker, market (2026-08-27)
- `에스키아닉스 → SK하이닉스`: ticker, market (2026-08-27)
- `엔비어 → 엔비디아`: ticker, market (2026-08-27)
- `엘파벳 → 알파벳`: ticker, market (2026-08-27)
- `오남이 → 모나미`: ticker, market (2026-08-27)
- `오라늄 → 우라늄`: ticker, market (2026-08-27)
- `우라님 → 우라늄`: ticker, market (2026-08-27)
- `워닝 IPS → 원익IPS`: ticker, market (2026-08-27)
- `유라늄 → 우라늄`: ticker, market (2026-08-27)
- `주성 엔지리어링 → 주성엔지니어링`: ticker, market (2026-08-27)
- `채치T → 챗지피티`: ticker, market (2026-08-27)
- `코스고 → 코스닥`: ticker, market (2026-08-27)
- `코이브 → 코어위브`: ticker, market (2026-08-27)
- `하이네스 → 하이닉스`: ticker, market (2026-08-27)
- `하이니스 → 하이닉스`: ticker, market (2026-08-27)
- `하이니프 → 하이닉스`: ticker, market (2026-08-27)
- `하이렉스 → 하이닉스`: ticker, market (2026-08-27)
- `하인스 → 하이닉스`: ticker, market (2026-08-27)
- `하잉스 → 하이닉스`: ticker, market (2026-08-27)

### Changed
- `소부 장단도 → 소부장도`: right_count (2026-08-27)
- `소부 장단들 → 소부장들`: right_count (2026-08-27)
- `소부 장단안에서 → 소부장 안에서`: right_count (2026-08-27)
- `소부 장단에 → 소부장에`: right_count (2026-08-27)
- `소부 장단을 → 소부장을`: right_count (2026-08-27)
- `소부 장단이 → 소부장이`: right_count (2026-08-27)

### Added
- `소부 장단도 → 소부장도` (2026-08-27)
- `소부 장단들 → 소부장들` (2026-08-27)
- `소부 장단안에서 → 소부장 안에서` (2026-08-27)
- `소부 장단에 → 소부장에` (2026-08-27)
- `소부 장단을 → 소부장을` (2026-08-27)
- `소부 장단이 → 소부장이` (2026-08-27)

### Removed
- `소부 장단 → 소부장` (2026-08-27)

### Changed
- `3,억짜리 → 3천억짜리`: right_count (2026-08-27)
- `3무기 → 3분기`: right_count (2026-08-27)
- `4쪽 보행 → 사족 보행`: right_count (2026-08-27)
- `5,억짜리 → 5천억짜리`: right_count (2026-08-27)
- `70 750조 → 750조`: right_count (2026-08-27)
- `7라노급 → 7나노급`: right_count (2026-08-27)
- `ACBM → HBM`: right_count (2026-08-27)
- `ACDS → HTS`: right_count (2026-08-27)
- `AMAMD → AMD`: right_count (2026-08-27)
- `AM대 → AMD`: right_count (2026-08-27)
- `DT 5 → DDR5`: right_count (2026-08-27)
- `FFC → FOMC`: right_count (2026-08-27)
- `FMC → FOMC`: right_count (2026-08-27)
- `HBN → HBM`: right_count (2026-08-27)
- `HCBM → HBM`: right_count (2026-08-27)
- `IS% → ISC`: right_count (2026-08-27)
- `K뷰T → K뷰티`: right_count (2026-08-27)
- `MCD → MACD`: right_count (2026-08-27)
- `MDI → 엔비디아`: right_count (2026-08-27)
- `M비디아 → 엔비디아`: right_count (2026-08-27)
- `SK 하이네스 → SK 하이닉스`: right_count (2026-08-27)
- `SK 하이스 → SK하이닉스`: right_count (2026-08-27)
- `SK 하이하스 → SK하이닉스`: right_count (2026-08-27)
- `SK 하인 → SK하이닉스`: right_count (2026-08-27)
- `SKS → SK하이닉스`: right_count (2026-08-27)
- `SK니스 → SK하이닉스`: right_count (2026-08-27)
- `SK닉스 → SK하이닉스`: right_count (2026-08-27)
- `SK하닉스 → SK하이닉스`: right_count (2026-08-27)
- `SK하잉 → SK하이닉스`: right_count (2026-08-27)
- `SM0봉 → S&P500 일봉`: right_count (2026-08-27)
- `SMP → 에스앤피`: right_count (2026-08-27)
- `S아닉스 → SK하이닉스`: right_count (2026-08-27)
- `XAI → xAI`: right_count (2026-08-27)
- `가이더스 → 가이던스`: right_count (2026-08-27)
- `감만해도 → 감안해도`: right_count (2026-08-27)
- `갤러시 → 갤럭시`: right_count (2026-08-27)
- `경원자 → 경영자`: right_count (2026-08-27)
- `공매돌 → 공매도`: right_count (2026-08-27)
- `공배도 → 공매도`: right_count (2026-08-27)
- `기적 분석 → 기술적 분석`: right_count (2026-08-27)
- `김에비디아 → 엔비디아`: right_count (2026-08-27)
- `나마토건 → 남화토건`: right_count (2026-08-27)
- `나상은 → 나스닥은`: right_count (2026-08-27)
- `남마토건 → 남화토건`: right_count (2026-08-27)
- `남마토원 → 남화토건`: right_count (2026-08-27)
- `남화통원 → 남화토건`: right_count (2026-08-27)
- `노크먼트 → 노코멘트`: right_count (2026-08-27)
- `단도체 → 반도체`: right_count (2026-08-27)
- `대원전설 → 대원전선`: right_count (2026-08-27)
- `등뜸이는 → 등 떠미는`: right_count (2026-08-27)
- `라이언 라이엇 → 라이엇`: right_count (2026-08-27)
- `마이러크럼 → 마이크론`: right_count (2026-08-27)
- `마이콘 테크놀로지 → 마이크론 테크놀로지`: right_count (2026-08-27)
- `마이크 테크놀로지 → 마이크론 테크놀로지`: right_count (2026-08-27)
- `마이크로님 → 마이크론`: right_count (2026-08-27)
- `매도체 → 반도체`: right_count (2026-08-27)
- `머비의 법칙 → 머피의 법칙`: right_count (2026-08-27)
- `머표 법칙 → 머피의 법칙`: right_count (2026-08-27)
- `미국체 → 미국채`: right_count (2026-08-27)
- `반도지 → 반도체`: right_count (2026-08-27)
- `반조체 → 반도체`: right_count (2026-08-27)
- `밤도체 → 반도체`: right_count (2026-08-27)
- `밸루에이션 → 밸류에이션`: right_count (2026-08-27)
- `변동상 → 변동성`: right_count (2026-08-27)
- `변합기 → 변압기`: right_count (2026-08-27)
- `보스턴 다이네믹스 → 보스턴 다이내믹스`: right_count (2026-08-27)
- `본동성 → 변동성`: right_count (2026-08-27)
- `브드컴 → 브로드컴`: right_count (2026-08-27)
- `블랙락 → 블랙록`: right_count (2026-08-27)
- `비슷하라 → 비스타라`: right_count (2026-08-27)
- `삼성근자 → 삼성전자`: right_count (2026-08-27)
- `삼성원자 → 삼성전자`: right_count (2026-08-27)
- `삼성자 → 삼성전자`: right_count (2026-08-27)
- `삼성전나 → 삼성전자`: right_count (2026-08-27)
- `삼성제카인 → 삼성전자`: right_count (2026-08-27)
- `서브라임 모기지 → 서브프라임 모기지`: right_count (2026-08-27)
- `셀트리오 → 셀트리온`: right_count (2026-08-27)
- `수납매 → 순환매`: right_count (2026-08-27)
- `슈머로이드 → 휴머노이드`: right_count (2026-08-27)
- `스페이스섹스 → 스페이스X`: right_count (2026-08-27)
- `스페이스엑스 → 스페이스X`: right_count (2026-08-27)
- `시가 총의 → 시가총액`: right_count (2026-08-27)
- `시카총 → 시가총액`: right_count (2026-08-27)
- `신형증권 → 신영증권`: right_count (2026-08-27)
- `실험률 → 실업률`: right_count (2026-08-27)
- `아모래 퍼시픽 → 아모레퍼시픽`: right_count (2026-08-27)
- `아이비 → IBM`: right_count (2026-08-27)
- `업항 → 업황`: right_count (2026-08-27)
- `에스키아닉스 → SK하이닉스`: right_count (2026-08-27)
- `엔비어 → 엔비디아`: right_count (2026-08-27)
- `엔트로피 → 앤트로픽`: right_count (2026-08-27)
- `엔트로픽 → 앤트로픽`: right_count (2026-08-27)
- `엘파벳 → 알파벳`: right_count (2026-08-27)
- `역초세 → 역추세`: right_count (2026-08-27)
- `영업익 → 영업이익`: right_count (2026-08-27)
- `오남이 → 모나미`: right_count (2026-08-27)
- `오라늄 → 우라늄`: right_count (2026-08-27)
- `올리브형 → 올리브영`: right_count (2026-08-27)
- `우라님 → 우라늄`: right_count (2026-08-27)
- `워닝 IPS → 원익IPS`: right_count (2026-08-27)
- `유라늄 → 우라늄`: right_count (2026-08-27)
- `유상진자 → 유상증자`: right_count (2026-08-27)
- `장기체 → 장기채`: right_count (2026-08-27)
- `제약 바위 → 제약 바이오`: right_count (2026-08-27)
- `종목면 → 종목명`: right_count (2026-08-27)
- `주성 엔지리어링 → 주성엔지니어링`: right_count (2026-08-27)
- `줄린이의 법칙 → 주린이의 법칙`: right_count (2026-08-27)
- `지정확전 리스크 → 지정학적 리스크`: right_count (2026-08-27)
- `지정확정 리스크 → 지정학적 리스크`: right_count (2026-08-27)
- `지진난주 → 지지난주`: right_count (2026-08-27)
- `채치T → 챗지피티`: right_count (2026-08-27)
- `컨센스 → 컨센서스`: right_count (2026-08-27)
- `코사 넣어 → 코스닥 넣어`: right_count (2026-08-27)
- `코스고 → 코스닥`: right_count (2026-08-27)
- `코스하고 → 코스닥으로`: right_count (2026-08-27)
- `코싹이 → 코스닥이`: right_count (2026-08-27)
- `코이브 → 코어위브`: right_count (2026-08-27)
- `파운트리 → 파운드리`: right_count (2026-08-27)
- `펀더멘탈 → 펀더멘털`: right_count (2026-08-27)
- `하이네스 → 하이닉스`: right_count (2026-08-27)
- `하이니스 → 하이닉스`: right_count (2026-08-27)
- `하이니프 → 하이닉스`: right_count (2026-08-27)
- `하이렉스 → 하이닉스`: right_count (2026-08-27)
- `하이퍼스러들 → 하이퍼스케일러들`: right_count (2026-08-27)
- `하인스 → 하이닉스`: right_count (2026-08-27)
- `하잉스 → 하이닉스`: right_count (2026-08-27)
- `해제 펀드 → 헤지 펀드`: right_count (2026-08-27)
- `해치 펀드 → 헤지 펀드`: right_count (2026-08-27)
- `휴먼노이드 → 휴머노이드`: right_count (2026-08-27)

Three pairs left the snapshot after a full-corpus recheck found sentences where
replacing them damages ordinary Korean. Two were withdrawn outright: `하스` is
spoken inside `하이퍼스케일러들`, and `SPB` stands for both `SPV` and `S&P`, so
neither key can be made safe. The third was **narrowed, not withdrawn** —
`바위 → 바이오` became `제약 바위 → 제약 바이오`, because 34 of its 71 corpus
matches were correct and the rest were the ordinary word for rock. A removal
here means the key was unsafe as written, not that every past application of it
was wrong.

### Added
- `HBN → HBM` (2026-08-27)
- `MDI → 엔비디아` (2026-08-27)
- `SK니스 → SK하이닉스` (2026-08-27)
- `SK닉스 → SK하이닉스` (2026-08-27)
- `SK하닉스 → SK하이닉스` (2026-08-27)
- `SMP → 에스앤피` (2026-08-27)
- `S아닉스 → SK하이닉스` (2026-08-27)
- `가이더스 → 가이던스` (2026-08-27)
- `공매돌 → 공매도` (2026-08-27)
- `김에비디아 → 엔비디아` (2026-08-27)
- `단도체 → 반도체` (2026-08-27)
- `마이러크럼 → 마이크론` (2026-08-27)
- `매도체 → 반도체` (2026-08-27)
- `반도지 → 반도체` (2026-08-27)
- `반조체 → 반도체` (2026-08-27)
- `밤도체 → 반도체` (2026-08-27)
- `밸루에이션 → 밸류에이션` (2026-08-27)
- `변동상 → 변동성` (2026-08-27)
- `본동성 → 변동성` (2026-08-27)
- `브드컴 → 브로드컴` (2026-08-27)
- `비슷하라 → 비스타라` (2026-08-27)
- `삼성원자 → 삼성전자` (2026-08-27)
- `삼성자 → 삼성전자` (2026-08-27)
- `삼성전나 → 삼성전자` (2026-08-27)
- `스페이스섹스 → 스페이스X` (2026-08-27)
- `스페이스엑스 → 스페이스X` (2026-08-27)
- `시카총 → 시가총액` (2026-08-27)
- `아이비 → IBM` (2026-08-27)
- `에스키아닉스 → SK하이닉스` (2026-08-27)
- `엔비어 → 엔비디아` (2026-08-27)
- `엘파벳 → 알파벳` (2026-08-27)
- `영업익 → 영업이익` (2026-08-27)
- `오남이 → 모나미` (2026-08-27)
- `오라늄 → 우라늄` (2026-08-27)
- `우라님 → 우라늄` (2026-08-27)
- `유라늄 → 우라늄` (2026-08-27)
- `제약 바위 → 제약 바이오` (2026-08-27)
- `채치T → 챗지피티` (2026-08-27)
- `컨센스 → 컨센서스` (2026-08-27)
- `코이브 → 코어위브` (2026-08-27)
- `파운트리 → 파운드리` (2026-08-27)
- `하이니프 → 하이닉스` (2026-08-27)
- `하이렉스 → 하이닉스` (2026-08-27)
- `하인스 → 하이닉스` (2026-08-27)

### Removed
- `SPB → SPV` (2026-08-27)
- `바위 → 바이오` (2026-08-27)
- `하스 → 하이닉스` (2026-08-27)

### Changed
- `FMC → FOMC`: evidence, auditor_models, approved_at (2026-08-27)
- `M비디아 → 엔비디아`: evidence, auditor_models, approved_at (2026-08-27)
- `SKS → SK하이닉스`: evidence, auditor_models, approved_at (2026-08-27)
- `펀더멘탈 → 펀더멘털`: evidence, auditor_models, approved_at (2026-08-27)
- `하이니스 → 하이닉스`: evidence, auditor_models, approved_at (2026-08-27)

### Added
- Initial public snapshot: 89 verified confusion pairs (tier A/B, enabled)
  exported 2026-08-13 from the upstream production dictionary — stock names,
  finance terms, and number damage from Korean finance-YouTube auto-captions.
  Full-corpus frequencies (`corpus_count`) from a 595-video scan.
- `evidence` field (2026-08-13): verification provenance (`human` /
  `auditor-consensus` / `goldset-alignment`) separated from `tier`, which
  remains an authority ordering.
- Benchmark: frozen eval set, trap set, scorer, and three replacement baselines
  (naive / word-boundary / production-guarded) with per-round verification
  numbers.

### Changed
- Benchmark promoted to `mini-v0.2` (2026-08-23): the trap set grew from 14 to
  40 hand-written sentences, chosen from a mechanical risk ranking
  (`benchmark/mine_traps.py`), and the eval set from 456 to 482 items. Baseline
  net scores moved accordingly (boundary 96.0% -> 88.7%) and are **not
  comparable across benchmark versions**; both are recorded in
  `benchmark/README.md`. No `data/` pair changed.
- Benchmark evaluation set is now append-only: item ids derive from the pair
  rather than its position, and existing items are carried across unchanged when
  the snapshot grows. Ids from `mini-v0` do not carry over to `mini-v0.2`.
- Benchmark: first LLM reference row (2026-08-23) — `claude-opus-5`, no
  dictionary, mean of 3 runs: 61.2% net against the dictionary's 88.7%, with
  four times fewer over-corrections and 114 confident wrong answers. Runner,
  manifest and per-run results are committed; the run itself needs credentials
  and is not part of scoring.
