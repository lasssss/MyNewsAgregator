import urllib.request
import json


def get_weather(lat: float, lon: float) -> dict | None:
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"weather_code,wind_speed_10m_max"
        f"&timezone=auto&forecast_days=3"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DailyNews/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


WMO_CODES = {
    0: "Ясно", 1: "Малооблачно", 2: "Облачно", 3: "Пасмурно",
    45: "Туман", 48: "Инейный туман",
    51: "Морось", 53: "Морось", 55: "Сильная морось",
    61: "Дождь", 63: "Дождь", 65: "Сильный дождь",
    71: "Снег", 73: "Снег", 75: "Сильный снег",
    77: "Снежные зёрна", 80: "Ливень", 81: "Ливень", 82: "Сильный ливень",
    85: "Снег с дождём", 86: "Сильный снег с дождём",
    95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
}

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def format_weather(data: dict, city: str) -> str:
    c = data["current"]
    d = data["daily"]

    code = c.get("weather_code", 0)
    desc = WMO_CODES.get(code, f"Код {code}")
    temp = c["temperature_2m"]
    feels = c["apparent_temperature"]
    hum = c["relative_humidity_2m"]
    wind = c["wind_speed_10m"]
    precip = c.get("precipitation", 0)

    lines = [
        f"<b>Погода — {city}</b>",
        f"<b>Сейчас:</b> {desc}",
        f"  Температура: {temp:+.0f}°C (ощущается {feels:+.0f}°C)",
        f"  Влажность: {hum}%",
        f"  Ветер: {wind:.0f} м/с",
    ]
    if precip > 0:
        lines.append(f"  Осадки: {precip} мм")

    lines.append("")
    lines.append("<b>Прогноз:</b>")
    for i in range(1, min(4, len(d["time"]))):
        from datetime import datetime
        dt = datetime.fromisoformat(d["time"][i])
        wd = WEEKDAYS[dt.weekday()]
        code_d = d["weather_code"][i]
        desc_d = WMO_CODES.get(code_d, "")
        t_min = d["temperature_2m_min"][i]
        t_max = d["temperature_2m_max"][i]
        p_sum = d["precipitation_sum"][i]
        wind_max = d["wind_speed_10m_max"][i]
        lines.append(
            f"  <b>{wd} {dt.day}.{dt.month}</b>: {desc_d} "
            f"{t_min:+.0f}…{t_max:+.0f}°C, ветер {wind_max:.0f} м/с"
        )
        if p_sum > 0:
            lines[-1] += f", дождь {p_sum} мм"

    return "\n".join(lines)
