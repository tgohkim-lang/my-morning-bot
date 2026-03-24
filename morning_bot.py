import yfinance as yf
import telegram
import asyncio
import os
import requests
from bs4 import BeautifulSoup

# GitHub Secrets에서 가져오기
TELEGRAM_TOKEN = os.getenv('8632215729:AAFYJgpBnJ5Jq5FSzVb05X1BfeR2MoUyWkI')
CHAT_ID = os.getenv('165044932')

async def get_weather():
    """대구 날씨 정보를 가져옵니다."""
    try:
        url = "https://wttr.in/Daegu?format=%C+%t"
        response = requests.get(url)
        return response.text.strip()
    except: return "확인 불가"

async def get_cnn_fear_greed():
    """CNN Fear & Greed Index를 가져옵니다."""
    try:
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        data = response.json()
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        return f"{score} ({rating})"
    except: return "확인 불가"

async def get_market_data():
    """환율 및 미국 3대 지수를 가져옵니다."""
    indices = {
        "환율(USD/KRW)": "KRW=X",
        "다우존스(^DJI)": "^DJI",
        "S&P 500(^GSPC)": "^GSPC",
        "나스닥(^IXIC)": "^IXIC"
    }
    results = {}
    for name, ticker in indices.items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            current = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            change = ((current - prev) / prev) * 100
            mark = "🔺" if change > 0 else "🔹"
            
            if "환율" in name:
                results[name] = f"{current:,.2f}원 ({mark}{abs(change):.2f}%)"
            else:
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
        f"☀️ **오늘의 경제 비서 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧭 **CNN 공포지수:** `{cnn_index}`\n"
        f"💵 **원/달러 환율:** `{market['환율(USD/KRW)']}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 증시 3대 지수**\n"
        f"· 다우: `{market['다우존스(^DJI)']}`\n"
        f"· S&P500: `{market['S&P 500(^GSPC)']}`\n"
        f"· 나스닥: `{market['나스닥(^IXIC)']}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 성공적인 하루 되세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
