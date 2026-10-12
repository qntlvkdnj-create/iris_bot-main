import threading
import time

import requests
from iris import ChatContext


GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_HEADERS = {"User-Agent": "iris-bot-weather/1.0"}

WEATHER_DESCRIPTIONS = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "착빙 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    56: "약한 어는 이슬비",
    57: "강한 어는 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    66: "약한 어는 비",
    67: "강한 어는 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "천둥번개",
    96: "우박을 동반한 천둥번개",
    99: "강한 우박을 동반한 천둥번개",
}

_geocoding_cache = {}
_geocoding_lock = threading.Lock()
_last_geocoding_request = 0.0


def _get_location(location_name):
    global _last_geocoding_request

    cache_key = location_name.casefold()
    with _geocoding_lock:
        if cache_key in _geocoding_cache:
            return _geocoding_cache[cache_key]

        delay = 1.0 - (time.monotonic() - _last_geocoding_request)
        if delay > 0:
            time.sleep(delay)

        response = requests.get(
            GEOCODING_URL,
            params={"q": location_name, "format": "jsonv2", "limit": 1},
            headers=GEOCODING_HEADERS,
            timeout=10,
        )
        _last_geocoding_request = time.monotonic()

    response.raise_for_status()
    results = response.json()
    if not isinstance(results, list):
        raise ValueError("Unexpected geocoding response")
    if not results:
        return None

    result = results[0]
    try:
        location = {
            "name": result["name"],
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
        }
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("Invalid geocoding result") from e

    _geocoding_cache[cache_key] = location
    return location


def get_weather(chat: ChatContext):
    command = chat.message.command
    location_name = command[1:-2].strip()
    if not location_name:
        chat.reply("지역명을 붙여 입력해주세요. 예: !서울날씨")
        return

    try:
        location = _get_location(location_name)
        if location is None:
            chat.reply(f"'{location_name}' 지역을 찾을 수 없습니다.")
            return

        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        current = data.get("current") if isinstance(data, dict) else None
        if not isinstance(current, dict):
            raise ValueError("Unexpected weather response")

        weather_code = current["weather_code"]
        if not isinstance(weather_code, int):
            raise ValueError("Invalid weather code")
        description = WEATHER_DESCRIPTIONS.get(weather_code, "알 수 없음")
        result = (
            f"{location['name']} 현재 날씨 ({current['time']})\n"
            f"날씨: {description}\n"
            f"기온: {current['temperature_2m']}°C "
            f"(체감 {current['apparent_temperature']}°C)\n"
            f"습도: {current['relative_humidity_2m']}%\n"
            f"바람: {current['wind_speed_10m']} km/h\n"
            "출처: Open-Meteo, OpenStreetMap"
        )
    except (
        requests.exceptions.RequestException,
        KeyError,
        TypeError,
        ValueError,
    ) as e:
        print(f"날씨 조회 실패 ({location_name}): {e}")
        chat.reply("날씨 조회에 실패했습니다. 잠시 후 다시 시도해주세요.")
        return

    chat.reply(result)
