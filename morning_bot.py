import yfinance as yf
import telegram
import asyncio
import requests
import os
from datetime import datetime

# GitHub Secrets 설정 (또는 직접 입력)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') or '본인의_토큰'
CHAT_ID = os.environ.get('CHAT_ID') or '본인의_ID'

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
            # 5일치 데이터를 가져와서 가장 최신(마지막) 2개를 비교합니다.
            data = yf.Ticker(ticker).history(period="5d")
            
            if len(data) >= 2:
                curr = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2]
                
                # 만약 수치가 nan이면 그 이전 데이터를 탐색
                if any(map(lambda x: str(x).lower() == 'nan', [curr, prev])):
                    res[name] = "장 휴무"
                    continue

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
                res[name] = "확인중"
        except:
            res[name] = "N/A"
    return res

async def main():
    print("🚀 경제 지표 수집 시작...")
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
        print("❌ 토큰 설정 오류")
        return

    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
        print("✅ 전송 성공!")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
