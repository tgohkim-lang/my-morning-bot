import yfinance as yf
import telegram
import asyncio
import os
import requests

# GitHub Secrets에서 가져오기 (절대 실제 값을 여기에 적지 마세요!)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    """대구 날씨 정보를 가져오고 깨진 문자를 정리합니다."""
    try:
        # 대구(Daegu) 날씨, 언어는 한국어(lang=ko)로 설정
        url = "https://wttr.in/Daegu?format=%C+%t&lang=ko"
        response = requests.get(url, timeout=10)
        # 깨진 온도 표시(Â°)를 정상적인 °로 치환
        weather_text = response.text.strip().replace("Â", "")
        return weather_text
    except: return "확인 불가"

async def get_cnn_fear_greed():
    """CNN Fear & Greed Index를 더 튼튼한 경로로 가져옵니다."""
    try:
        # 브라우저처럼 보이게 헤더를 강화하여 차단을 피합니다.
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        
        # 점수에 따라 직관적인 이모지 추가
        emoji = "😱" if score < 30 else "😨" if score < 45 else "😐" if score < 55 else "😊" if score < 75 else "🤑"
        return f"{score} ({rating}) {emoji}"
    except: 
        return "조회 일시 중단"

async def get_market_data():
    """환율 및 미국 3대 지수를 가져옵니다."""
    indices = {
        "환율": "KRW=X",
        "다우": "^DJI",
        "S&P500": "^GSPC",
        "나스닥": "^IXIC"
    }
    results = {}
    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="5d")
            current = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100
            # 상승/하락에 따른 이모지 설정
            mark = "🔺" if change > 0 else "🔹"
            results[name] = f"{current:,.2f} ({mark}{abs(change):.2f}%)"
        except:
            results[name] = "조회 불가"
    return results

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("에러: Secrets 설정이 되어있지 않습니다.")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    weather = await get_weather()
    cnn_index = await get_cnn_fear_greed()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **CNN 공포지수:** `{cnn_index}`\n"
        f"💵 **원/달러 환율:** `{market['환율']}`원\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 3대 증시**\n"
        f"· 다우: `{market['다우']}`\n"
        f"· S&P500: `{market['S&P500']}`\n"
        f"· 나스닥: `{market['나스닥']}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 화이팅하세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
