import yfinance as yf
import telegram
import asyncio
import os
import requests
import google.generativeai as genai

# 1. 환경 변수 설정 (GitHub Secrets에서 가져오기)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 2. Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 분석할 유튜브 채널 정보 (수페TV)
YOUTUBE_CHANNELS = {
    "수페TV": "UC38B_9K2LzEunN2y8a80uMw"
}

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "정보 확인 불가"

async def get_market_sentiment():
    """시장 위험도 측정 (VIX 활용)"""
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        if vix >= 20:
            return f"🚨 **VIX {vix:.2f} - 변동성 높음 (주의)**"
        return f"✅ VIX {vix:.2f} - 변동성 낮음 (안정)"
    except: return "지수 조회 불가"

async def get_gemini_summary(title, description):
    """Gemini AI를 활용한 3줄 핵심 요약"""
    try:
        prompt = f"""
        당신은 전문 경제 비서입니다. 아래 유튜브 영상의 제목과 설명을 바탕으로 
        바쁜 직장인이 핵심만 파악할 수 있게 한국어로 3줄 요약해 주세요.
        
        영상 제목: {title}
        영상 설명: {description}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "AI 요약 생성 중 오류가 발생했습니다."

async def get_latest_youtube_brief():
    """최신 영상을 검색하고 요약본을 생성합니다."""
    briefs = []
    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1&type=video"
            res = requests.get(url).json()
            video = res['items'][0]
            
            v_title = video['snippet']['title']
            v_desc = video['snippet']['description']
            v_url = f"https://youtu.be/{video['id']['videoId']}"
            
            # Gemini 요약 호출
            summary = await get_gemini_summary(v_title, v_desc)
            
            briefs.append(f"📺 **{name} 최신 영상**\n📌 {v_title}\n{summary}\n🔗 [영상 바로가기]({v_url})")
        except:
            continue
    return "\n\n".join(briefs) if briefs else "새로운 영상 정보가 없습니다."

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
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("필수 설정 값이 부족합니다.")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    # 데이터 수집
    weather = await get_weather()
    sentiment = await get_market_sentiment()
    youtube_section = await get_latest_youtube_brief()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 위험도:** {sentiment}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{youtube_section}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 **금융 지표**\n"
        f"· 환율: `{market['환율']}`\n"
        f"· 미 10년물 국채금리: `{market['미 국채 10년물']}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 증시 마감**\n"
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
