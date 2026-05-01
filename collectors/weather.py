"""
天气数据采集 - 使用 wttr.in 免费 API

用于关联天气与客流关系
"""
from .base import BaseCollector


class WeatherCollector(BaseCollector):
    name = "weather"

    def collect(self):
        records = []
        try:
            # wttr.in 免费天气 API
            resp = self.fetch("https://wttr.in/Shanghai?format=j1", timeout=10)
            data = resp.json()

            current = data.get("current_condition", [{}])[0]
            temp = float(current.get("temp_C", 0))
            feels_like = float(current.get("FeelsLikeC", 0))
            humidity = int(current.get("humidity", 0))
            desc_cn = current.get("lang_zh", [{}])[0].get("value", "") if current.get("lang_zh") else current.get("weatherDesc", [{}])[0].get("value", "")
            wind_speed = float(current.get("windspeedKmph", 0))

            records.extend([
                ("temperature", temp, "℃", "measured", {"feels_like": feels_like}),
                ("humidity", humidity, "%", "measured", {}),
                ("wind_speed", wind_speed, "km/h", "measured", {}),
            ])

            # 今日高低温
            weather_today = data.get("weather", [{}])[0]
            if weather_today:
                max_temp = float(weather_today.get("maxtempC", 0))
                min_temp = float(weather_today.get("mintempC", 0))
                records.extend([
                    ("temperature_max", max_temp, "℃", "measured", {}),
                    ("temperature_min", min_temp, "℃", "measured", {}),
                ])

            # 天气描述
            records.append(("weather_desc", 0, desc_cn, "measured",
                            {"raw": current}))

        except Exception as e:
            records.append(("weather_status", 0, "error", "unavailable",
                            {"error": str(e)}))

        return records
