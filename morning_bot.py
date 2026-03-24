import requests
import telegram
import asyncio

# ==========================================
# ⚠️ 본인의 정보를 정확히 입력하세요!
# ==========================================
TELEGRAM_TOKEN = '8632215729:AAFYJgpBnJ5Jq5FSzVb05X1BfeR2MoUyWkI'
CHAT_ID = '165044932'

async def get_exchange_rate():
    """안정적인 API를 통해 원/달러 환율을 가져옵니다."""
    # 무료 환율 API (가입 없이 사용 가능한 주소입니다)
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # 'KRW'(한국 원화) 값만 쏙 골라냅니다.
        krw_rate = data['rates']['KRW']
        return f"{float(krw_rate):,.2f}" # 천단위 콤마 추가
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return "조회 불가"

async def main():
    """메시지를 구성하고 전송합니다."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    rate = await get_exchange_rate()
    
    # 메시지 디자인 (Markdown 형식)
    message = (
        f"☀️ **좋은 아침입니다!**\n\n"
        f"💵 **오늘의 외환 정보**\n"
        f"━━━━━━━━━━━━━━\n"
        f"· 원/달러 환율: `{rate}`원\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"오늘도 멋진 하루 보내세요! 🍀"
    )
    
    try:
        async with bot:
            await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
        print("✅ 텔레그램 메시지 전송 성공!")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())
