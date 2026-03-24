import yfinance as yf
import telegram
import asyncio
import os
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+온도:%t+체감:%f&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "날씨 확인 불가"

async def get_vix_index():
    """VIX 지수를 가져오고 상태에 따라 강조 기호를 붙입니다."""
    try:
        vix = yf.Ticker("^VIX").history(period="2d")
        current = vix['Close'].iloc[-1]
        prev = vix['Close'].iloc[-2]
        diff = current - prev
        mark = "🔺" if diff > 0 else "🔹"
        
        # 공포 상태(보통 20~25 이상)일 때 굵게 강조 및 이모지 변경
        status_msg = f"{current:.2f} ({mark}{abs(diff):.2f})"
        if current >= 20:
            return f"🚨 **{status_msg} (공포 주의)**"
        return f"😊 {status_msg} (안정)"
    except: return "조회 불가"

async def get_market_data():
    """환율, 국채 금리 및 미국 3대 지수를 가져옵니다."""
    indices = {
        "환율": "KRW=X",
        "미 국채 10년물": "^TNX", # 10년물 국채 금리 티커
        "다우존스": "^DJI",
        "S&P 500": "^GSPC",
        "나스닥": "^IXIC"
    }
    results = {}
    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="5d")
            current = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            diff = current - prev
            change_pct = (diff / prev) * 100
            
            mark = "🔺" if diff > 0 else "🔹"
            
            if "국채" in name:
                # 국채 금리는 % 단위로 표시
                results[name] = f"{current:.2f}% ({mark}{abs(diff):.2f})"
            elif "환율" in name:
                results[name] = f"{current:,.2f}원 ({mark}{abs(diff):.2f})"
            else:
                results[name] = f"{current:,.2f} ({mark}{abs(diff):.2f} / {change_pct:+.2f}%)"
        except:
            results[name] = "조회 불가"
    return results

async def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    weather = await get_weather()
    vix = await get_vix_index()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 공포지수(VIX):** {vix}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 **금융 지표**\n"
        f"· 환율: `{market['환율']}`\n"
        f"· 미 10년물 국채금리: `{market['미 국채 10년물']}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 3대 증시 마감**\n"
        f"· 다우: `{market['다우존스']}`\n"
        f"· S&P500: `{market['S&P 500']}`\n"
        f"· 나스닥: `{market['나스닥']}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 성공적인 투자와 하루 되세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
