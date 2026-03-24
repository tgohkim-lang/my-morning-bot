import yfinance as yf
import telegram
import asyncio
import os
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    """대구 날씨 정보를 가져오고 한글 인코딩 문제를 해결합니다."""
    try:
        # 인코딩 문제를 피하기 위해 영문으로 가져온 뒤 핵심만 추출하거나, 직접 인코딩을 지정합니다.
        url = "https://wttr.in/Daegu?format=%C+%t&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8' # 한글 깨짐 방지 강제 설정
        weather_text = response.text.strip().replace("Â", "")
        return weather_text
    except: return "확인 불가"

async def get_cnn_fear_greed():
    """CNN 지수가 계속 막힐 경우를 대비해, 더 유연한 방식으로 가져옵니다."""
    try:
        # CNN에서 직접 제공하는 데이터 주소입니다.
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        # 깃허브 서버임을 숨기기 위해 더 정교한 헤더를 사용합니다.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            score = int(data['now']['value'])
            rating = data['now']['value_text']
            return f"{score} ({rating})"
        else:
            return "CNN 서버 응답 지연"
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
            mark = "🔺" if change > 0 else "🔹"
            results[name] = f"{current:,.2f} ({mark}{abs(change):.2f}%)"
        except:
            results[name] = "조회 불가"
    return results

async def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    weather = await get_weather()
    cnn_index = await get_cnn_fear_greed()
    market = await get_market_data()
    
    # 메시지 가독성을 높이기 위해 디자인 수정
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
