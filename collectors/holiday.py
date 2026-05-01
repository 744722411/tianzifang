"""
节假日/工作日判断

节假日对客流影响巨大，需要单独标记
"""
from datetime import datetime, timedelta, timezone
from .base import BaseCollector

TZ_CST = timezone(timedelta(hours=8))

# 2026年中国法定节假日（需要每年更新）
# 格式: (月, 日, 名称)
CN_HOLIDAYS_2026 = [
    (1, 1, "元旦"),
    (1, 2, "元旦假期"),
    (1, 3, "元旦假期"),
    (2, 16, "除夕"),
    (2, 17, "春节"),
    (2, 18, "春节假期"),
    (2, 19, "春节假期"),
    (2, 20, "春节假期"),
    (2, 21, "春节假期"),
    (2, 22, "春节假期"),
    (4, 4, "清明节"),
    (4, 5, "清明假期"),
    (4, 6, "清明假期"),
    (5, 1, "劳动节"),
    (5, 2, "劳动节假期"),
    (5, 3, "劳动节假期"),
    (5, 4, "劳动节假期"),
    (5, 5, "劳动节假期"),
    (5, 31, "端午节"),
    (6, 1, "端午假期"),
    (6, 2, "端午假期"),
    (10, 1, "国庆节"),
    (10, 2, "国庆假期"),
    (10, 3, "国庆假期"),
    (10, 4, "国庆假期"),
    (10, 5, "国庆假期"),
    (10, 6, "国庆假期"),
    (10, 7, "国庆假期"),
]

# 调休工作日（需要每年更新）
CN_WORKDAYS_2026 = [
    (1, 4, "元旦调休上班"),
    (2, 14, "春节调休上班"),
    (2, 28, "春节调休上班"),
    (4, 26, "劳动节调休上班"),
    (10, 10, "国庆调休上班"),
]


class HolidayCollector(BaseCollector):
    name = "holiday"

    def collect(self):
        now = self.now()
        month, day = now.month, now.day
        weekday = now.weekday()  # 0=周一

        is_holiday = 0
        holiday_name = ""

        # 检查是否法定节假日
        for m, d, name in CN_HOLIDAYS_2026:
            if m == month and d == day:
                is_holiday = 1
                holiday_name = name
                break

        # 检查是否调休工作日
        is_workday_override = False
        for m, d, name in CN_WORKDAYS_2026:
            if m == month and d == day:
                is_workday_override = True
                holiday_name = name
                break

        # 判断是否工作日
        is_workday = 1 if (weekday < 5 and not is_holiday) or is_workday_override else 0

        return [
            ("is_holiday", is_holiday, "bool", "measured",
             {"holiday_name": holiday_name}),
            ("is_workday", is_workday, "bool", "measured",
             {"weekday": weekday, "is_workday_override": is_workday_override}),
            ("weekday", weekday, "day", "measured", {}),
        ]
