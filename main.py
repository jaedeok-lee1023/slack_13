import os
import sys
import datetime
import arrow
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from kurly import clusters

# 🎯 한국 공휴일 목록 (YYYY-MM-DD 형식)
HOLIDAYS = {
    "2025-01-01",  # 신정
    "2025-03-01",  # 삼일절
    "2025-05-05",  # 어린이날
    "2025-05-06",  # 대체공휴일
    "2025-10-06",  # 추석
    "2025-10-07",  # 추석연휴
    "2025-10-09",  # 한글날
    "2025-12-25",  # 크리스마스
}

# 📆 오늘 날짜 가져오기
today = datetime.date.today().strftime("%Y-%m-%d")

# 🚫 오늘이 공휴일이면 실행하지 않고 종료
if today in HOLIDAYS:
    print(f"📢 오늘({today})은 공휴일이므로 실행하지 않습니다.")
    sys.exit(0)

# 환경 변수에서 Slack 토큰 로드
load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

def send_slack_message(message, channel):
    try:
        client = WebClient(token=SLACK_TOKEN)
        client.chat_postMessage(channel=channel, text=message)
    except SlackApiError as e:
        print(f"⚠️ Error sending message to {channel} : {e}")

def main():
    for cluster in clusters:
        # 메시지 제목 설정
        header = f":loudspeaker: *『인사총무팀 공지』* <!channel>\n\n"

        notice_msg = (
            f"안녕하세요? 평택 클러스터 구성원 여러분!\n"
            f"\n"
            f" *직원식당 다음주 식단표* 공유 드립니다.\n"
            f"\n"
            f"\n"
            f"* (Click) :point_right: <https://docs.google.com/spreadsheets/d/1p5loEO1j5kxUAvK6TKV-Muyc8LUYlPsq0eanzHELSQs/edit?gid=156845326#gid=156845326|평택클러스터 다음주 식단표>*\n\n"
            f":k체크: *메뉴와 원산지는 식자재 수급 사정에 따라 변경 될 수 있습니다.*\n"
            f"\n\n"
            f"\n\n"
            f"이번주 식단표는 아래 링크에서 확인 가능합니다.\n"
            f"* (Click) :point_right: <https://sites.google.com/view/kurly-logistics-recruit/%EC%A3%BC%EA%B0%84-%EC%8B%9D%EB%8B%A8%ED%91%9C-%EC%95%88%EB%82%B4/%ED%8F%89%ED%83%9D%EC%84%BC%ED%84%B0-%EC%A3%BC%EA%B0%84-%EB%A9%94%EB%89%B4%ED%91%9C-%EC%95%88%EB%82%B4?authuser=0|평택클러스터 이번주 식단표>*\n"
            f"\n"
            f"\n"
            f"감사합니다. 😊\n\n"
        )
 
# 메시지 본문
        body = header + notice_msg

        # 슬랙 채널에 전송
        send_slack_message(body, cluster.channel)

if __name__ == "__main__":
    main()
