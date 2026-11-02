# 지수보다 강한 종목 대시보드 — 1단계: 데이터 받기

장 마감 후 하루 한 번 데이터를 `data/` 폴더에 저장합니다.
- 국내 종목: **나무증권(NH투자증권) namuh PLUG** Open API (공식 SDK `nhplug`)
- 국내 지수(코스피·코스닥), 미국 지수·종목: yfinance (무료)

## 준비 (본인 PC에서, 처음 한 번)
1. 파이썬 3.10 이상 설치 ("Add python.exe to PATH" 체크)
2. 이 폴더에서 `pip install -r requirements.txt`
3. 나무증권 PLUG 포털(www.nhplug.com)에서 앱키·앱시크릿 발급
4. `copy .env.example .env` → `notepad .env` 로 열어 앱키·앱시크릿 입력 후 저장
5. `test_login.bat` 더블클릭 → 1)~3)이 모두 성공인지 확인

## 실행
```
python fetch_data.py kr --limit 50   # 국내 시총 상위 50종목만 먼저 테스트
python fetch_data.py us --limit 20   # 미국 20종목만 먼저 테스트
python fetch_data.py kr              # 국내 전체 (약 2,500종목, 초당 4회라 10~15분)
python fetch_data.py us              # S&P500 전체 (1~2분)
```

## 만들어지는 파일
| 파일 | 내용 |
|---|---|
| data/kr_index_ohlc.csv, data/kr_ohlc.csv | 지수·종목 일봉 (캔들차트용) |
| data/kr_index.csv | 코스피·코스닥 지수 종가 |
| data/kr_stocks.csv | 국내 종목 목록 (시총 큰 순서) |
| data/kr_close.csv | 국내 종목 종가 (날짜 x 종목코드) |
| data/us_index.csv | S&P500·나스닥 지수 종가 |
| data/us_close.csv | S&P500 종목 종가 (날짜 x 티커) |

## 사용한 나무증권 PLUG API
- 토큰: SDK가 자동 발급·24시간 캐시 (`~/.nhplug/`)
- 종목 목록: 종목마스터 `m_new_stock` (ETF·ETN, 거래정지, 정리매매 제외)
- 일봉: `/krstock/quote/v1/period` (gubun=1 일봉, 정규장 기준)
- PLUG에는 코스피·코스닥 지수 시세 API가 없어 지수는 yfinance(^KS11, ^KQ11)로 받음

---|---|
| data/kr_index_ohlc.csv, data/kr_ohlc.csv | 지수·종목 일봉 (시가·고가·저가·종가, 캔들차트용) |
| data/kr_index.csv | 코스피·코스닥 지수 종가 (약 1년) |
| data/kr_stocks.csv | 국내 종목 목록 |
| data/kr_close.csv | 국내 종목 종가 (날짜 x 종목코드) |
| data/us_index.csv | S&P500·나스닥 지수 종가 |
| data/us_close.csv | S&P500 종목 종가 (날짜 x 티커) |

## 사용한 키움 API
- au10001 접근토큰 발급 (`/oauth2/token`)
- ka10099 종목정보 리스트 (`/api/dostk/stkinfo`)
- ka20006 업종(지수) 일봉 (`/api/dostk/chart`, 가격이 100배 정수라 100으로 나눔)
- ka10081 주식 일봉 (`/api/dostk/chart`, 수정주가 적용)
- 호출 제한: 토큰당 초당 5회 (초과 시 1700 오류, 자동 재시도)

---

# 2·3단계: "강한 종목" 기준과 순위 계산 (`screener.py`)

| 지표 | 계산 |
|---|---|
| RS20 | 종목 20일 수익률 − 지수 20일 수익률 (%p) |
| RS60 | 종목 60일 수익률 − 지수 60일 수익률 (%p) |
| 버팀 | 최근 60일 중 지수 하락일에 (종목 등락률 − 지수 등락률)의 평균 (%p) |
| 버팀승률 | 그 하락일 중 종목이 지수보다 덜 빠지거나 오른 날의 비율 (%) |

- **종합점수**: RS20·RS60·버팀을 각각 0~100 백분위로 바꿔 30% / 30% / 40%로 가중평균
- **강한 종목 표시**: RS20, RS60, 버팀이 모두 0보다 큰 종목
- 비교 지수: 코스피 종목은 코스피, 코스닥 종목은 코스닥, 미국은 S&P500
- **종목만지지**: 지수가 최근 120일 안에 직전 저점(그 전 60일 최저 종가)을 깼는데, 종목은 같은 기간 자기 저점 아래로 한 번도 마감하지 않은 상태
- **강한 종목** = RS강세(RS20·RS60·버팀 모두 플러스) 또는 종목만돌파 또는 종목만지지
- **종목만돌파**: 지수가 아직 최근 120일 전고점 아래인데, 종목은 그 전고점 날까지의 자기 최고 종가를 넘어선 상태
- 가중치는 `screener.py` 맨 위 `WEIGHTS`에서 바꿀 수 있어요.

```
python screener.py kr    # data/kr_ranking.csv 생성
python screener.py us    # data/us_ranking.csv 생성
```

# 4단계: 대시보드 (`build_dashboard.py`)

```
python build_dashboard.py   # dashboard.html 생성 → 브라우저로 열기
```
- 위쪽: **왼쪽 지수 캔들차트, 오른쪽 종목 캔들차트**를 같은 날짜로 나란히 비교
  - 지수 전고점(최근 120거래일 최고 종가) 날짜에 세로 점선, 금색 점선은 전고점/종목 기준선
  - 종목이 기준선을 넘은 날에 동그라미 표시
  - 아래에 "지수는 전고점 대비 몇 %, 종목은 언제 돌파해서 지금 몇 %" 설명이 자동으로 나옴
- 아래쪽: 종합점수 상위 50종목 표 (누르면 위 비교 차트가 바뀜), 열 제목 클릭으로 정렬
- 비교 차트 위 "전고점 돌파 / 저점 지지" 버튼으로 두 가지 비교를 바꿔 볼 수 있음 (저점 지지는 파란 실선으로 직전 저점·자기 저점 표시)
- 필터: "종목만 돌파", "종목만 지지", "강한 종목만"


# 한 번에 실행 (윈도우)
장 마감 후 `run_all.bat` 더블클릭 → 데이터 받기, 순위 계산, 대시보드 열기까지 자동.
