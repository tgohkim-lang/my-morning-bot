import yfinance as yf
import telegram
import asyncio
import os
import requests
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# 1. 환경 변수 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# 2. Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 구독 채널 목록
YOUTUBE_CHANNELS = {
    "수페TV": "UC38B_9K2LzEunN2y8a80uMw",
    "서대리TV": "UCtQkxwZkrruYdy2bVNNW-Rw",
    "마경환": "UC-vS_m_9vUInZ0XN2Yk20sw",
    "YTN 뉴스(검증용)": "UChlgI3UPOq6qOTZK5S5Be1Q"
}

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "날씨 확인 불가"

async def get_market_sentiment():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        return f"{vix:.2f}"
    except: return "확인 불가"

async def get_gemini_summary(title, description):
    try:
        prompt = f"경제 유튜버 영상 제목: {title}\n설명: {description}\n위 내용을 번호를 매겨 3줄로 핵심만 요약해줘."
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "AI 요약 실패"

async def get_latest_youtube_brief():
    briefs = []
    debug_logs = []
    now = datetime.now(timezone.utc)
    
    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            # 채널의 업로드 목록 ID (UC -> UU)
            playlist_id = "UU" + channel_id[2:]
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={YOUTUBE_API_KEY}&playlistId={playlist_id}&part=snippet,contentDetails&maxResults=2"
            res = requests.get(url).json()
            
            if 'error' in res:
                debug_logs.append(f"❌ {name}: API 에러({res['error']['message']})")
                continue
                
            items = res.get('items', [])
            if not items:
                debug_logs.append(f"❓ {name}: 영상 목록 비어있음")
                continue

            for item in items:
                v_title = item['snippet']['title']
                pub_at = item['snippet']['publishedAt']
                pub_time = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                
                # 시차 고려하여 36시간 이내 영상이면 채택
                if now - pub_time <= timedelta(hours=36):
                    v_id = item['contentDetails']['videoId']
                    v_desc = item['snippet']['description']
                    summary = await get_gemini_summary(v_title, v_desc)
                    briefs.append(f"📺 **{name}**\n📌 {v_title}\n{summary}\n🔗 https://youtu.be/{v_id}")
                    break 
        except Exception as e:
            debug_logs.append(f"⚠️ {name} 시스템 에러: {str(e)}")
            
    result_text = "\n\n".join(briefs) if briefs else "최근 24시간 내 새 영상이 없습니다."
    # 디버깅 정보를 메시지 하단에 작게 추가 (문제가 해결되면 이 부분은 나중에 지우면 됩니다)
    if debug_logs:
        result_text += "\n\n🔍 **시스템 로그:**\n" + "\n".join(debug_logs)
        
    return result_text

async def get_market_data():
    # S&P 500(^GSPC) 다시 추가
    indices = {"환율": "KRW=X", "국채10년": "^TNX", "다우": "^DJI", "나스닥": "^IXIC", "S&P500": "^GSPC"}
    results = {}
    for name, ticker in indices.items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            diff = curr - prev
            results[name] = f"{curr:,.2f}({'+' if diff > 0 else ''}{diff:,.2f})"
        except: results[name] = "N/A"
    return results

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    # 병렬 실행으로 속도 향상
    weather, vix, market, youtube_section = await asyncio.gather(
        get_weather(), get_market_sentiment(), get_market_data(), get_latest_youtube_brief()
    )
    
    msg = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 위험도 (VIX):** `{vix}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"{youtube_section}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 **금융 지표**\n"
        f"· 환율: `{market['환율']}원`\n"
        f"· 미 국채 10년물: `{market['국채10년']}%`\n"
        f"· 다우: `{market['다우']}`\n"
        f"· 나스닥: `{market['나스닥']}`\n"
        f"· **S&P 500:** `{market['S&P500']}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 화이팅입니다! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
