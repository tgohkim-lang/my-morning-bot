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

# 3. 구독 채널 목록 (YouTube 채널 ID)
YOUTUBE_CHANNELS = {
    "수페TV": "UC38B_9K2LzEunN2y8a80uMw",
    "서대리TV": "UCtQkxwZkrruYdy2bVNNW-Rw",
    "마경환": "UC-vS_m_9vUInZ0XN2Yk20sw",
    "YTN 뉴스(검증용)": "UChlgI3UPOq6qOTZK5S5Be1Q"
}

async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        return res.text.strip().replace("Â", "")
    except: return "날씨 확인 불가"

async def get_market_sentiment():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        return f"{vix:.2f}"
    except: return "N/A"

async def get_gemini_summary(title, description):
    try:
        prompt = f"다음 경제 영상의 내용을 핵심만 3줄 요약해줘.\n제목: {title}\n설명: {description}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "AI 요약 생성 실패"

async def get_upload_playlist_id(channel_id):
    """채널 ID로부터 업로드 플레이리스트 ID를 직접 가져옵니다."""
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels?id={channel_id}&part=contentDetails&key={YOUTUBE_API_KEY}"
        res = requests.get(url).json()
        return res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    except:
        return "UU" + channel_id[2:] # 실패 시 기본 규칙 적용

async def get_youtube_content():
    briefs = []
    logs = []
    now = datetime.now(timezone.utc)
    
    for name, ch_id in YOUTUBE_CHANNELS.items():
        try:
            # 업로드 ID 직접 조회 (에러 방지 핵심)
            playlist_id = await get_upload_playlist_id(ch_id)
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={YOUTUBE_API_KEY}&playlistId={playlist_id}&part=snippet,contentDetails&maxResults=2"
            res = requests.get(url).json()
            
            if 'error' in res:
                logs.append(f"❌ {name}: {res['error']['message']}")
                continue
                
            for item in res.get('items', []):
                pub_at = item['snippet']['publishedAt']
                pub_time = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                
                # 36시간 이내 영상만 포함
                if now - pub_time <= timedelta(hours=36):
                    v_id = item['contentDetails']['videoId']
                    v_title = item['snippet']['title']
                    v_desc = item['snippet']['description']
                    summary = await get_gemini_summary(v_title, v_desc)
                    briefs.append(f"📺 **{name}**\n📌 {v_title}\n{summary}\n🔗 https://youtu.be/{v_id}")
                    break
        except Exception as e:
            logs.append(f"⚠️ {name} 시스템 오류: {str(e)}")
            
    youtube_text = "\n\n".join(briefs) if briefs else "최근 올라온 새 영상 정보가 없습니다."
    if logs:
        youtube_text += "\n\n🔍 **로그:**\n" + "\n".join(logs)
    return youtube_text

async def get_market_data():
    # 지표 리스트 (국채금리 ^TNX 포함)
    indices = {"환율": "KRW=X", "국채10년": "^TNX", "다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
    res = {}
    for name, ticker in indices.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if data.empty:
                res[name] = "N/A"
                continue
            curr = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            diff = curr - prev
            mark = "🔺" if diff > 0 else "🔹"
            
            if name == "국채10년":
                res[name] = f"{curr:.2f}% ({mark}{abs(diff):.2f})"
            elif name == "환율":
                res[name] = f"{curr:,.2f}원 ({mark}{abs(diff):.2f})"
            else:
                res[name] = f"{curr:,.2f} ({mark}{abs(diff):.2f})"
        except: res[name] = "조회 실패"
    return res

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    # 데이터 수집
    weather = await get_weather()
    vix = await get_market_sentiment()
    market = await get_market_data()
    youtube_section = await get_youtube_content()
    
    msg = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 **대구 날씨:** `{weather}`\n"
        f"🧭 **시장 위험도(VIX):** `{vix}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"{youtube_section}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 **금융 지표**\n"
        f"· 환율: `{market.get('환율', 'N/A')}`\n"
        f"· 국채 10년: `{market.get('국채10년', 'N/A')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 증시 마감**\n"
        f"· 다우: `{market.get('다우', 'N/A')}`\n"
        f"· **S&P 500:** `{market.get('S&P500', 'N/A')}`\n"
        f"· 나스닥: `{market.get('나스닥', 'N/A')}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 성투하세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
