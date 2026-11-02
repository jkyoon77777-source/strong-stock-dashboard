"""나무증권 PLUG 로그인 진단. 키 값은 화면에 출력하지 않아요.  사용법: python test_login.py"""
import os
from dotenv import load_dotenv

load_dotenv(".env") or load_dotenv(".env.txt")
k, s = os.getenv("NHPLUG_APP_KEY", ""), os.getenv("NHPLUG_APP_SECRET", "")
print(f"앱키 길이 {len(k.strip())}, 시크릿 길이 {len(s.strip())}")
if not k or not s:
    raise SystemExit(".env 에 NHPLUG_APP_KEY / NHPLUG_APP_SECRET 두 줄을 넣어 주세요.")

from nhplug import NhplugError, call, get_base_url, get_token, status_of

try:
    get_token()
    print("1) 토큰 발급: 성공!  서버:", get_base_url())
except NhplugError as e:
    raise SystemExit(f"1) 토큰 발급 실패: {e.category} {e.code} {e.message}")

data = call("/krstock/quote/v1/currentPrice", {"iem_cd": "005930", "market_cd": "KRX"})
price = (data.get("Output_0") or {}).get("stck_prpr")
print("2) 삼성전자 현재가:", price if price else f"못 받음 ({status_of(data)[1]})")

import nh_client
df = nh_client.stock_daily("005930", "1", days=5)
print("3) 삼성전자 최근 5일 종가:", df["close"].tolist())
print("\n모두 성공이면 run_all.bat 을 실행하세요.")
