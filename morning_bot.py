import yfinance as yf
import telegram
import asyncio
import os
import requests

# GitHub Secrets에서 안전하게 가져오기
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_weather():
    """대구 날씨 정보를 가져오고 한글 인코딩을 처리합니다."""
    try:
        # 가독성을 위해 구분자(|) 추가
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except:
        return "날씨 정보 확인 불가"

async def get_cnn_fear_greed():
    """CNN 공포지수를 가져오되, 실패 시 VIX 지수로 자동 대체합니다."""
    try:
        url = "https://production.dataviz.cnn.io/index/feargreed/static/daily"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['now']['value'])
        rating = data['now']['value_text']
        
        # 공포 단계(45 이하)일 때 사이렌 이모지와 굵게 강조
        if score <= 45:
            return f"🚨 **{score} ({rating})**"
        return f"{score} ({rating})"
    except:
        try:
            # CNN 차단 시 야후 파이낸스에서 VIX 지수 추출
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(period="1d")
            vix_score = vix_data['Close'].iloc[-1]
            # VIX가 20 이상이면 시장 공포 상태로 간주
            if vix_score >= 20:
                return f"🚨 **{vix_score:.2f} (VIX 공포)**"
            return f"{vix_score:.2f} (VIX 안정)"
        except:
            return "지수 조회 일시 중단"

async def get_market_data():
    """환율, 국채 금리 및 미국 3대 지수의 등락폭을 계산합니다."""
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
                # 금리는 소수점 2자리 %로 표시
                results[name] = f"{current:.2f}% ({mark}{abs(diff):.2f})"
            elif "환율" in name:
                results[name] = f"{current:,.2f}원 ({mark}{abs(diff):.2f}원)"
            else:
                # 지수는 포인트 등락과 퍼센트 함께 표시
                results[name] = f"{current:,.2f} ({mark}{abs(diff):.2f} / {change_pct:+.2f}%)"
        except:
            results[name] = "조회 불가"
    return results

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 CHAT_ID가 설정되지 않았습니다.")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    weather = await get_weather()
    fear_index = await get_cnn_fear_greed()
    market = await get_market_data()
    
    # 메시지 레이아웃 구성
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 공포지수:** {fear_index}\n"
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
        f"오늘도 성공적인 투자와 활기찬 하루 되세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
