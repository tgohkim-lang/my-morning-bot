import yfinance as yf
import telegram
import asyncio
import os
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    try:
        # 대구 날씨 가독성 개선 (공백 추가)
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "확인 불가"

async def get_cnn_fear_greed():
    """블로그 참조 API 방식 (가장 확실한 경로)"""
    try:
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        # 헤더를 더 실제 브라우저와 똑같이 구성하여 차단을 방지합니다.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://www.cnn.com',
            'Referer': 'https://www.cnn.com/'
        }
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        
        # 상태에 따른 이모지 설정
        if score <= 25: emoji = "😱 (극도의 공포)"
        elif score <= 45: emoji = "😨 (공포)"
        elif score <= 55: emoji = "😐 (중립)"
        elif score <= 75: emoji = "😊 (탐욕)"
        else: emoji = "🤑 (극도의 탐욕)"
        
        # 🟢 공포 단계일 때 굵게 강조
        status_msg = f"{score} - {rating} {emoji}"
        if score <= 45:
            return f"🚨 **{status_msg}**"
        return status_msg
    except:
        # 만약 CNN이 또 막히면 차선책으로 VIX를 자동으로 가져오게 설계
        try:
            vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
            return f"{vix:.2f} (CNN 조회실패로 VIX 대체)"
        except: return "조회 일시 중단"

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
    cnn_fear = await get_cnn_fear_greed()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **CNN 공포지수:** {cnn_fear}\n"
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
