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

# 3. 구독 채널 목록 (정밀 확인된 ID입니다)
YOUTUBE_CHANNELS = {
    "수페TV": "UC38B_9K2LzEunN2y8a80uMw",
    "서대리TV": "UCtQkxwZkrruYdy2bVNNW-Rw",
    "마경환": "UC-vS_m_9vUInZ0XN2Yk20sw"
}

async def get_weather():
    """대구 날씨 조회"""
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except: return "날씨 정보 확인 불가"

async def get_market_sentiment():
    """시장 위험도 측정 (VIX)"""
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        if vix >= 20:
            return f"🚨 **VIX {vix:.2f} - 변동성 높음 (주의)**"
        return f"✅ VIX {vix:.2f} - 변동성 낮음 (안정)"
    except: return "지수 조회 불가"

async def get_gemini_summary(title, description):
    """Gemini AI 3줄 요약"""
    try:
        prompt = f"경제 유튜버의 영상이야. 제목과 설명을 보고 핵심을 번호를 매겨 3줄 요약해줘.\n제목: {title}\n설명: {description}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "AI 요약 생성 중 오류가 발생했습니다."

async def get_latest_youtube_brief():
    """가장 확실하게 업로드 목록 ID를 직접 찾아서 영상을 가져옵니다."""
    briefs = []
    now = datetime.now(timezone.utc)
    
    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            # 1단계: 채널 정보를 직접 조회하여 '업로드 재생목록 ID'를 정확히 가져옵니다.
            ch_url = f"https://www.googleapis.com/youtube/v3/channels?key={YOUTUBE_API_KEY}&id={channel_id}&part=contentDetails"
            ch_res = requests.get(ch_url).json()
            
            if 'items' not in ch_res or not ch_res['items']:
                print(f"[{name}] 채널 정보를 찾을 수 없습니다. ID를 확인해주세요.")
                continue
                
            upload_playlist_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # 2단계: 해당 재생목록에서 최신 영상 3개를 확인합니다. (Shorts 포함 방지용)
            pl_url = f"https://www.googleapis.com/youtube/v3/playlistItems?key={YOUTUBE_API_KEY}&playlistId={upload_playlist_id}&part=snippet,contentDetails&maxResults=3"
            pl_res = requests.get(pl_url).json()
            
            for item in pl_res.get('items', []):
                pub_at = item['snippet']['publishedAt']
                pub_time = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                
                # 확인 범위를 48시간으로 넓혀서 시차 및 누락을 방지합니다.
                if now - pub_time <= timedelta(hours=48):
                    v_id = item['contentDetails']['videoId']
                    v_title = item['snippet']['title']
                    v_desc = item['snippet']['description']
                    v_full_url = f"https://youtu.be/{v_id}"

                    summary = await get_gemini_summary(v_title, v_desc)
                    briefs.append(f"📺 **{name} 새 영상**\n📌 {v_title}\n{summary}\n🔗 [영상 바로가기]({v_full_url})")
                    print(f"[{name}] 영상 발견: {v_title}")
                    break # 채널당 가장 최신 영상 1개만 처리
        except Exception as e:
            print(f"[{name}] 처리 중 에러: {e}")
            continue
            
    return "\n\n".join(briefs) if briefs else "최근 24시간 동안 올라온 새로운 영상 정보가 없습니다."

async def get_market_data():
    """금융 지표 수집"""
    indices = {"환율": "KRW=X", "미 국채 10년물": "^TNX", "다우존스": "^DJI", "S&P 500": "^GSPC", "나스닥": "^IXIC"}
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
            if "국채" in name: results[name] = f"{current:.2f}% ({mark}{abs(diff):.2f})"
            elif "환율" in name: results[name] = f"{current:,.2f}원 ({mark}{abs(diff):.2f}원)"
            else: results[name] = f"{current:,.2f} ({mark}{abs(diff):.2f} / {change_pct:+.2f}%)"
        except: results[name] = "조회 불가"
    return results

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
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
        f"· 환율: `{market.get('환율', '조회 불가')}`\n"
        f"· 미 10년물 국채금리: `{market.get('미 국채 10년물', '조회 불가')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 **미국 증시 마감**\n"
        f"· 다우: `{market.get('다우존스', '조회 불가')}`\n"
        f"· S&P500: `{market.get('S&P 500', '조회 불가')}`\n"
        f"· 나스닥: `{market.get('나스닥', '조회 불가')}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 성공적인 투자와 하루 되세요! 🍀"
    )
    
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
