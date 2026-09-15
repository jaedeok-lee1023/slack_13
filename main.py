import os
import sys
import json
import base64
import datetime
import urllib.request
import urllib.error
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from kurly import clusters

# 🎯 한국 공휴일 목록 (YYYY-MM-DD 형식)
HOLIDAYS = {
    "2026-01-01",  # 신정
    "2026-02-16",  # 설 연휴
    "2026-02-17",  # 설날
    "2026-02-18",  # 설 연휴
    "2026-03-02",  # 대체공휴일
    "2026-05-05",  # 어린이날
    "2026-05-25",  # 대체공휴일
    "2026-06-03",  # 지방선거
    "2026-08-17",  # 대체공휴일
    "2026-09-24",  # 추석 연휴
    "2026-09-25",  # 추석
    "2026-10-05",  # 대체공휴일
    "2026-10-09",  # 한글날
    "2026-12-25",  # 크리스마스
}

# 📄 식단표 스프레드시트
SPREADSHEET_ID = "11GCv7_yIem_b_cZfRLztHHce2_C630MdfdVdt4OalT8"

# 📆 오늘 날짜 가져오기
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")

# 🚫 오늘이 공휴일이면 실행하지 않고 종료
if today_str in HOLIDAYS:
    print(f"📢 오늘({today_str})은 공휴일이므로 실행하지 않습니다.")
    sys.exit(0)

# 환경 변수 로드
load_dotenv()
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
GAS_WEBAPP_URL = os.environ.get("GAS_WEBAPP_URL")  # Apps Script 웹앱 배포 URL


def get_week_numbers(base_date):
    """
    대한민국(ISO 8601) 기준 주차 계산.
    - 이번주: base_date가 속한 주의 ISO 주차
    - 다음주: base_date + 7일이 속한 주의 ISO 주차
    (연말/연초 경계에서도 안전하게 동작하도록 날짜 이동 후 isocalendar 사용)
    """
    this_week = base_date.isocalendar()[1]
    next_week_date = base_date + datetime.timedelta(days=7)
    next_week = next_week_date.isocalendar()[1]
    return this_week, next_week


def get_week_info_from_gas(week_number):
    """
    Apps Script 웹앱에 특정 주차 정보를 물어본다.
    반환: {"url": ..., "image_bytes": bytes|None, "image_filename": str|None}
    웹앱 호출이 실패하거나 아직 해당 주차 탭이 없으면 url은 스프레드시트 기본 링크, image는 None.
    """
    fallback = {
        "url": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
        "image_bytes": None,
        "image_filename": None,
    }

    if not GAS_WEBAPP_URL:
        print("⚠️ GAS_WEBAPP_URL이 설정되지 않아 기본 링크를 사용합니다.")
        return fallback

    url = f"{GAS_WEBAPP_URL}?week={week_number}"
    try:
        with urllib.request.urlopen(url, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"⚠️ GAS 웹앱 호출 실패: {e}")
        return fallback

    if "error" in data:
        print(f"⚠️ {week_number}주차 탭 조회 실패: {data['error']}")
        return fallback

    result = {
        "url": data["url"],
        "image_bytes": None,
        "image_filename": None,
    }

    if data.get("imageBase64"):
        try:
            result["image_bytes"] = base64.b64decode(data["imageBase64"])
            result["image_filename"] = data.get("imageFileName") or f"{week_number}주차_식단표.jpg"
        except (ValueError, TypeError) as e:
            print(f"⚠️ 이미지 디코딩 실패: {e}")

    return result


def send_slack_notice(body, channel, image_bytes=None, image_filename=None):
    """
    이미지가 있으면 캡션(초기 코멘트)과 함께 파일로 업로드해서 미리보기가 바로 보이게 하고,
    이미지가 없으면 기존처럼 텍스트 메시지만 전송한다.
    """
    client = WebClient(token=SLACK_TOKEN)
    try:
        if image_bytes:
            client.files_upload_v2(
                channel=channel,
                file=image_bytes,
                filename=image_filename or "식단표.jpg",
                initial_comment=body,
            )
        else:
            client.chat_postMessage(channel=channel, text=body)
    except SlackApiError as e:
        print(f"⚠️ Error sending message to {channel} : {e}")


def main():
    this_week, next_week = get_week_numbers(today)
    print(f"📅 기준일: {today_str} / 이번주: {this_week}주차 / 다음주: {next_week}주차")

    # ✅ 이번주 정보도 다음주와 동일하게 GAS 웹앱에서 조회 (정적 SITE_URL 완전히 제거)
    this_week_info = get_week_info_from_gas(this_week)
    next_week_info = get_week_info_from_gas(next_week)

    this_week_sheet_url = this_week_info["url"]
    next_week_sheet_url = next_week_info["url"]

    for cluster in clusters:
        # 메시지 제목 설정
        header = f"*[공지｜직원식당 식단표 안내]*\n\n\n"
        notice_msg = (
            f"1. *중요도* : 하\n"
            f"2. *대상* : 평택 클러스터 임직원 전체\n"
            f"3. *주요 내용*\n\n"
            f"\n"
            f"안녕하세요? 평택 클러스터 구성원 여러분!\n\n"
            f"\n"
            f"*<{next_week_sheet_url}|직원식당 다음주 식단표>* 공유 드립니다.\n"
            f":k체크: *메뉴와 원산지는 식자재 수급 사정에 따라 변경 될 수 있습니다.*\n\n"
            f"\n"
            f"이번주 식단표는 <{this_week_sheet_url}|스프레드 시트>에서 확인 부탁드립니다.\n"
            f"\n"
            f"감사합니다. 😊\n\n"
        )

        # 메시지 본문
        body = header + notice_msg
        # 슬랙 채널에 전송 (이미지가 있으면 파일 업로드+캡션, 없으면 텍스트만)
        send_slack_notice(
            body,
            cluster.channel,
            image_bytes=next_week_info["image_bytes"],
            image_filename=next_week_info["image_filename"],
        )


if __name__ == "__main__":
    main()
