import yfinance as yf
import telegram
import asyncio
import os
import requests

TELEGRAM_TOKEN = os.getenv('8632215729:AAFYJgpBnJ5Jq5FSzVb05X1BfeR2MoUyWkI')
CHAT_ID = os.getenv('165044932')

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+%t"
        response = requests.get(url, timeout=10)
        return response.text.strip()
    except: return "확인 불가"

async def get_cnn_fear_greed():
    try:
        # CNN 지수를 제공하는 공개 API 활용 (가장 안정적)
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        return f"{score} ({rating})"
    except: return "확인 불가"

async def get_market_data():
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
