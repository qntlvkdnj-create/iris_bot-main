import requests
import pytz
from datetime import datetime
from iris import ChatContext


GIFT_CODES_URL = "https://wostools.net/api/gift-codes"


def get_gift_codes(chat: ChatContext):
    try:
        response = requests.get(GIFT_CODES_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if (
            not isinstance(data, dict)
            or data.get("success") is not True
            or not isinstance(data.get("codes"), list)
        ):
            raise ValueError("Unexpected gift-code API response")
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"선물 코드 조회 실패: {e}")
        chat.reply("선물 코드 조회에 실패했습니다. 잠시 후 다시 시도해주세요.")
        return

    active_codes = [
        code["code"]
        for code in data["codes"]
        if isinstance(code, dict)
        and code.get("status") == "active"
        and isinstance(code.get("code"), str)
        and code["code"].strip()
    ]
    checked_at = datetime.now(pytz.timezone("Asia/Seoul")).strftime(
        "%Y-%m-%d %H:%M"
    )

    if active_codes:
        result = (
            f"Whiteout Survival 활성 선물 코드\n조회 시각: {checked_at}\n\n"
            + "\n".join(f"• {code}" for code in active_codes)
        )
    else:
        result = f"현재 활성 선물 코드가 없습니다.\n조회 시각: {checked_at}"

    chat.reply(f"{result}\n\n출처: https://wostools.net/ko/gift-codes")
