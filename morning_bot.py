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
    "마경환": "UC-vS_m_9vUInZ0XN2Yk20sw"
}

# -----------------------------
# 날씨
# -----------------------------
async def get_weather():
    try:
        url = "https://wttr.in/Daegu?format=%C+|+온도:%t+|+체감:%f&lang=ko&m"
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text.strip().replace("Â", "")
    except:
        return "날씨 정보 확인 불가"

# -----------------------------
# 시장 심리
# -----------------------------
async def get_market_sentiment():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        if vix >= 20:
            return f"🚨 VIX {vix:.2f} - 변동성 높음 (주의)"
        return f"✅ VIX {vix:.2f} - 변동성 낮음 (안정)"
    except:
        return "지수 조회 불가"

# -----------------------------
# Gemini 요약
# -----------------------------
async def get_gemini_summary(title, description):
    try:
        if not description:
            description = "설명 없음"

        prompt = f"""
경제 유튜브 영상 요약.
핵심만 3줄, 번호로 정리.

제목: {title}
설명: {description}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "요약 실패 (원문 확인)"

# -----------------------------
# 유튜브 최신 영상 (핵심 수정 부분)
# -----------------------------
async def get_latest_youtube_brief():
    briefs = []
    now = datetime.now(timezone.utc)

    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet&order=date&maxResults=3&type=video"
            res = requests.get(url).json()

            for item in res.get('items', []):
                pub_at = item['snippet']['publishedAt']
                pub_time = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

                if now - pub_time <= timedelta(hours=30):
                    v_id = item['id']['videoId']
                    v_title = item['snippet']['title']
                    v_desc = item['snippet'].get('description', '')
                    v_url = f"https://youtu.be/{v_id}"

                    summary = await get_gemini_summary(v_title, v_desc)

                    briefs.append(
                        f"📺 **{name} 새 영상**\n"
                        f"📌 {v_title}\n"
                        f"{summary}\n"
                        f"🔗 {v_url}"
                    )
                    break

        except Exception as e:
            print(f"{name} 에러: {e}")
            continue

    return "\n\n".join(briefs) if briefs else "최근 24시간 신규 영상 없음"

# -----------------------------
# 시장 데이터
# -----------------------------
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

        except:
            results[name] = "조회 불가"

    return results

# -----------------------------
# 메인 실행
# -----------------------------
async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("토큰 없음")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    weather = await get_weather()
    sentiment = await get_market_sentiment()
    youtube = await get_latest_youtube_brief()
    market = await get_market_data()

    message = (
        f"☀️ **경제 비서 아침 브리핑**\n\n"
        f"📍 대구 날씨: `{weather}`\n"
        f"🧭 시장 위험도: {sentiment}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{youtube}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 금융 지표\n"
        f"· 환율: `{market.get('환율')}`\n"
        f"· 미 10년물: `{market.get('미 국채 10년물')}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇺🇸 미국 증시\n"
        f"· 다우: `{market.get('다우존스')}`\n"
        f"· S&P500: `{market.get('S&P 500')}`\n"
        f"· 나스닥: `{market.get('나스닥')}`\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 성공 투자 🍀"
    )

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

# 실행
if __name__ == "__main__":
    asyncio.run(main())
