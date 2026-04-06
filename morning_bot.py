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

# 3. 구독 채널 목록 (YTN 뉴스 추가로 즉각 검증)
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
    except: return "날씨 정보 확인 불가"

async def get_market_sentiment():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        return f"{vix:.2f}"
    except: return "확인 불가"

async def get_gemini_summary(title, description):
    try:
        prompt = f"경제 유튜버의 영상이야. 핵심 내용을 번호를 매겨 3줄 요약해줘.\n제목: {title}\n설명: {description}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "AI 요약 생성 중 오류"

async def get_latest_youtube_brief():
    briefs = []
    now = datetime.now(timezone.utc)
    print(f"--- 유튜브 검사 시작 (현재 서버 시간: {now}) ---")
    
    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            # 업로드 목록 ID 가져오기
            upload_playlist_id = "UU" + channel_id[2:]
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={YOUTUBE_API_KEY}&playlistId={upload_playlist_id}&part=snippet,contentDetails&maxResults=3"
            res = requests.get(url).json()
            
            if 'items' not in res:
                print(f"[{name}] API 응답 오류: {res.get('error', '알 수 없는 에러')}")
                continue

            for item in res['items']:
                v_title = item['snippet']['title']
                pub_at = item['snippet']['publishedAt']
                pub_time = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                diff = now - pub_time
                
                print(f"[{name}] 발견: {v_title} / 업로드: {pub_time} (지금으로부터 {diff.total_seconds()/3600:.1f}시간 전)")

                # 24시간 이내 영상만 필터링 (검증을 위해 28시간으로 소폭 상향)
                if diff <= timedelta(hours=28):
                    v_id = item['contentDetails']['videoId']
                    v_desc = item['snippet']['description']
                    v_full_url = f"https://youtu.be/{v_id}"

                    summary = await get_gemini_summary(v_title, v_desc)
                    briefs.append(f"📺 **{name} 새 영상**\n📌 {v_title}\n{summary}\n🔗 [영상 바로가기]({v_full_url})")
                    print(f" -> [선택됨] 24시간 이내 영상입니다.")
                    break # 채널당 최신 1개만
                else:
                    print(f" -> [제외] 24시간이 지났습니다.")
                    
        except Exception as e:
            print(f"[{name}] 에러 발생: {e}")
            continue
            
    return "\n\n".join(briefs) if briefs else "최근 24시간 동안 새로운 영상이 없습니다."

async def get_market_data():
    indices = {"환율": "KRW=X", "미 국채 10년물": "^TNX", "다우": "^DJI", "나스닥": "^IXIC"}
    results = {}
    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            data = t.history(period="5d")
            results[name] = f"{data['Close'].iloc[-1]:,.2f}"
        except: results[name] = "조회 불가"
    return results

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    weather = await get_weather()
    vix = await get_market_sentiment()
    youtube_section = await get_latest_youtube_brief()
    market = await get_market_data()
    
    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 위험도 (VIX):** `{vix}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"{youtube_section}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 **금융 지표**\n"
        f"· 환율: `{market['환율']}원` / 국채금리: `{market['미 국채 10년물']}%`\n"
        f"· 다우: `{market['다우']}` / 나스닥: `{market['나스닥']}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 화이팅입니다! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
