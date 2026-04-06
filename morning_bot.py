import yfinance as yf
import telegram
import asyncio
import os
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "정보 확인 불가"

async def get_market_sentiment():
    """CNN 공포지수 시도 후, 실패 시 VIX 지수로 전환하여 직관적 메시지 반환"""
    try:
        # 1차 시도: CNN Fear & Greed
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        
        # CNN은 점수가 낮을수록(45 이하) 공포
        if score <= 45:
            return f"🚨 **CNN {score} ({rating}) - 시장 공포**"
        return f"✅ CNN {score} ({rating}) - 시장 안정"
    except:
        try:
            # 2차 시도: VIX (CNN 차단 시)
            vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
            # VIX는 점수가 높을수록(20 이상) 공포
            if vix >= 20:
                return f"🚨 **VIX {vix:.2f} - 변동성 높음 (주의)**"
            return f"✅ VIX {vix:.2f} - 변동성 낮음 (안정)"
        except:
            return "지수 조회 불가"

async def get_market_data():
    indices = {
        "환율": "KRW=X",
        "미 국채 10년물": "^TNX",
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
                results[name] = f"{current:.2f}% ({mark}{abs(diff):.2f})"
            elif "환율" in name:
                results[name] = f"{current:,.2f}원 ({mark}{abs(diff):.2f}원)"
            else:
                results[name] = f"{current:,.2f} ({mark}{abs(diff):.2f} / {change_pct:+.2f}%)"
        except: results[name] = "조회 불가"
    return results

async def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    weather = await get_weather()
    sentiment = await get_market_sentiment()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 위험도:** {sentiment}\n"
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
