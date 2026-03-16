# backtest 패키지

RFM 대회 규정 기반 주간 리밸런싱 백테스트 프레임워크.

## 빠른 시작

```python
from backtest.data     import load_universe, download_prices, get_sector_map
from backtest.strategy import compute_target_weights
from backtest.engine   import run_backtest
from backtest.metrics  import print_report

universe   = load_universe()
prices     = download_prices(universe, start="2022-01-01", end="2026-04-01")
sector_map = get_sector_map(universe)

result = run_backtest(prices, compute_target_weights, sector_map)
print_report(result["nav"], result["turnover_log"], result["turnover_violations"])
```

## 전략 교체

`backtest/strategy.py`의 `compute_target_weights(prices)` 내부 로직만 수정하면 됩니다.

- **입력**: `pd.DataFrame` — 신호 계산 기준일(t)까지의 수정주가
- **출력**: `pd.Series` — `yf_ticker → 목표 비중` (합계가 1.0이 아니어도 됨)
- 제약조건(15% 한도, 섹터 비중 등)은 `engine.py`에서 자동 적용됩니다.

## 룩어헤드 바이어스

신호 계산 기준일과 체결 시점을 구분해야 합니다.

| 구분 | 신호 계산 | 체결 가정 | 비고 |
|------|-----------|-----------|------|
| **옵션 A** (현재 구현) | t일 종가까지 | t+1일 시가 (종가로 근사) | 룩어헤드 없음 ✅ |
| 옵션 B | t일 종가까지 | t일 종가 | 실전 불가 → 과대평가 ⚠️ |

옵션 A: `engine.py`에서 리밸런싱일 t의 수익은 이전 비중으로 계산하고, 새 비중은 t+1일부터 적용합니다.

옵션 B로 변경하려면 `run_backtest()`의 Step 1/2 순서를 바꾸면 됩니다.

## 주간 회전율 산출 공식

```
회전율(%) = (매수총액 + 매도총액) / 기간 평균 운용금액 × 0.5 × 100
```

순자산의 **10% 이상**을 주간 거래해야 위반이 아닙니다. 최대 **3회** 위반 허용.
대회 시스템 자동 체크 불가 → 이 코드에서 직접 추적합니다.

## DataGuide vs yfinance 수정주가

| 항목 | DataGuide | yfinance |
|------|-----------|----------|
| 방식 | 한국 회계기준 수정 | Backward-adjusted |
| 차이 발생 | 고배당·액면분할 종목 | 동일 |
| 사용법 | `load_prices_from_csv()` | `download_prices()` (기본값) |

## KOSPI200 섹터 비중 갱신

`config.py`의 `SECTOR_WEIGHTS`를 분기별로 갱신하세요.
출처: KOSPI200 구성 종목 공시 (한국거래소 정기 발표)

## 대회 제약조건 요약

| 제약 | 기준 |
|------|------|
| 단일 종목 최대 비중 | 15% (삼성전자 40%) |
| 섹터 비중 | KOSPI200 해당 섹터 × 2 이하 (≤5% 섹터는 최대 10%) |
| 소형주(시총 1조 미만) 합산 | 30% 이하 |
| 편입 불가 | 시총 1,000억 미만 / 5일 평균 거래대금 30억 미만 |
