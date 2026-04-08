import yfinance as yf
import telegram
import asyncio
import requests
from datetime import datetime

# ==========================================
# [인증 정보 입력]
# ==========================================
TELEGRAM_TOKEN = '본인의_텔레그램_토큰'
CHAT_ID = '본인의_채팅_ID'
# ==========================================

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        res = requests.get(url, timeout=10)
        return res.content.decode('utf-8').strip()
    except:
        return "날씨 정보 수집 불가"

async def get_market_data():
    # 다우(DJI), S&P500(GSPC), 나스닥(IXIC) 포함
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
            data = yf.Ticker(ticker).history(period="2d")
            if data.empty:
                res[name] = "데이터 없음"
                continue
                
            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
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
        except:
            res[name] = "N/A"
    return res

async def main():
    print("🚀 경제 지표 브리핑 수집 시작...")
    
    weather = await get_weather()
    market = await get_market_data()
    
    # 영상 관련 섹션을 완전히 제거한 메시지 폼
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

    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
        print("✅ 전송 성공!")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
