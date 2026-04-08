import yfinance as yf
import telegram
import asyncio
import requests
import os
import pandas as pd
from datetime import datetime

# GitHub Secrets
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        res = requests.get(url, timeout=10)
        return res.content.decode('utf-8').strip()
    except:
        return "날씨 정보 수집 불가"

async def get_market_data():
    indices = {
        "환율": "KRW=X", 
        "국채10년": "^TNX", 
        "다우": "^DJI",
        "S&P 500": "^GSPC", 
        "나스닥": "^IXIC", 
        "VIX": "^VIX"
    }
    res = {}
    
    for name, ticker in indices.items():
        try:
            # 데이터를 7일치 넉넉히 가져옵니다.
            df = yf.download(ticker, period="7d", progress=False)
            
            if not df.empty and len(df) >= 2:
                # 최신 데이터 2개를 선택 (NaN 값 제거 후 마지막 2개)
                valid_data = df['Close'].dropna()
                
                if len(valid_data) >= 2:
                    curr = float(valid_data.iloc[-1])
                    prev = float(valid_data.iloc[-2])
                    
                    diff = curr - prev
                    mark = "🔺" if diff > 0 else "🔹"
                    
                    if name == "국채10년":
                        res[name] = f"{curr:.2f}%({mark}{abs(diff):.2f})"
                    elif name == "환율":
                        res[name] = f"{curr:,.2f}원({mark}{abs(diff):.2f})"
                    elif name == "VIX":
                        res[name] = f"{curr:.2f}"
                    else:
                        res[name] = f"{curr:,.2f}({mark}{abs(diff):.2f})"
                else:
                    res[name] = "업데이트 중"
            else:
                res[name] = "데이터 확인 불가"
        except:
            res[name] = "N/A"
    return res

async def main():
    print("🚀 시장 데이터 정밀 수집 시작...")
    weather = await get_weather()
    market = await get_market_data()
    
    msg = (f"☀️ **경제 비서 아침 브리핑**\n\n"
           f"📍 **대구 날씨:** `{weather}`\n"
           f"🧭 **시장 위험도(VIX):** `{market.get('VIX', 'N/A')}`\n"
           f"━━━━━━━━━━━━━━\n"
           f"💵 **금융 지표**\n"
           f"· 환율: `{market.get('환율', 'N/A')}`\n"
           f"· 국채 10년: `{market.get('국채10년', 'N/A')}`\n"
           f"━━━━━━━━━━━━━━\n"
           f"🇺🇸 **미국 증시 마감**\n"
           f"· 다우: `{market.get('다우', 'N/A')}`\n"
           f"· S&P 500: `{market.get('S&P 500', 'N/A')}`\n"
           f"· 나스닥: `{market.get('나스닥', 'N/A')}`\n"
           f"━━━━━━━━━━━━━━\n"
           f"오늘도 화이팅! 🍀")

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ 설정 오류: Secrets를 확인하세요.")
        return

    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
        print("✅ 브리핑 전송 성공!")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
