#!/usr/bin/env python3
"""
田子坊人流数据 - 查询工具

用法:
    python analysis/query.py today          # 今日数据
    python analysis/query.py date 2026-05-01  # 指定日期
    python analysis/query.py weekday 5      # 周五的历史数据
    python analysis/query.py holiday         # 节假日 vs 工作日对比
    python analysis/query.py summary         # 数据概览
    python analysis/query.py forecast        # 未来预测（基于历史规律）
"""
import sys
import json
from datetime import datetime, timedelta, timezone
from config.db import get_conn

TZ_CST = timezone(timedelta(hours=8))


def show_today():
    now = datetime.now(TZ_CST)
    date_str = now.strftime("%Y-%m-%d")
    show_date(date_str)


def show_date(date_str):
    conn = get_conn()
    print(f"\n📊 {date_str} 田子坊数据")
    print("-" * 50)

    # 在园人数变化
    rows = conn.execute("""
        SELECT ts, value, confidence FROM crowd_data
        WHERE source = 'gov_tour' AND metric = 'in_park_count'
        AND date(ts) = ?
        ORDER BY ts
    """, (date_str,)).fetchall()

    if rows:
        print(f"\n🚶 在园人数 ({len(rows)} 条记录):")
        for r in rows:
            time_str = r["ts"][11:16]
            conf = "📍" if r["confidence"] == "measured" else "📐"
            print(f"  {time_str}  {conf} {int(r['value']):>6} 人")
    else:
        print("\n🚶 在园人数: 无数据")

    # 天气
    weather = conn.execute("""
        SELECT metric, value, unit FROM crowd_data
        WHERE source = 'weather' AND date(ts) = ?
    """, (date_str,)).fetchall()

    if weather:
        print(f"\n🌤 天气:")
        for w in weather:
            if w["metric"] == "weather_desc":
                print(f"  {w['unit']}")
            else:
                print(f"  {w['metric']}: {w['value']}{w['unit']}")

    # 节假日
    holiday = conn.execute("""
        SELECT raw_json FROM crowd_data
        WHERE source = 'holiday' AND metric = 'is_holiday'
        AND date(ts) = ?
        LIMIT 1
    """, (date_str,)).fetchone()

    if holiday:
        info = json.loads(holiday["raw_json"]) if holiday["raw_json"] else {}
        if info.get("holiday_name"):
            print(f"\n🎉 {info['holiday_name']}")

    # 日汇总
    summary = conn.execute("SELECT * FROM daily_summary WHERE date = ?", (date_str,)).fetchone()
    if summary:
        print(f"\n📈 日汇总:")
        print(f"  最大客流: {summary['max_crowd']} 人")
        print(f"  平均客流: {summary['avg_crowd']} 人")
        print(f"  峰值时段: {summary['peak_hour']}时")

    conn.close()


def show_weekday(weekday):
    """显示某星期几的历史统计"""
    conn = get_conn()
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    rows = conn.execute("""
        SELECT date, max_crowd, avg_crowd, peak_hour, is_holiday
        FROM daily_summary
        WHERE weekday = ? AND is_holiday = 0
        ORDER BY date DESC
        LIMIT 20
    """, (int(weekday),)).fetchall()

    print(f"\n📅 {day_names[int(weekday)]}历史数据 (最近{len(rows)}次)")
    print("-" * 60)
    if rows:
        for r in rows:
            print(f"  {r['date']}  最大:{r['max_crowd']:>5}  均值:{r['avg_crowd']:>5}  峰值:{r['peak_hour']}时")
    else:
        print("  暂无数据")
    conn.close()


def show_summary():
    """数据概览"""
    conn = get_conn()

    total_records = conn.execute("SELECT COUNT(*) as c FROM crowd_data").fetchone()["c"]
    total_days = conn.execute("SELECT COUNT(*) as c FROM daily_summary").fetchone()["c"]
    first = conn.execute("SELECT MIN(date) as d FROM daily_summary").fetchone()["d"]
    last = conn.execute("SELECT MAX(date) as d FROM daily_summary").fetchone()["d"]

    print(f"\n📊 数据概览")
    print("-" * 40)
    print(f"  总记录数: {total_records}")
    print(f"  日汇总天数: {total_days}")
    print(f"  时间范围: {first or 'N/A'} ~ {last or 'N/A'}")

    if total_days > 0:
        avg = conn.execute("SELECT AVG(avg_crowd) as a FROM daily_summary").fetchone()["a"]
        max_r = conn.execute("SELECT MAX(max_crowd) as m, date FROM daily_summary").fetchone()
        print(f"  全期平均客流: {avg:.0f} 人/时段")
        print(f"  历史最高: {max_r['m']} 人 ({max_r['date']})")

    conn.close()


def forecast():
    """基于历史数据预测未来客流"""
    conn = get_conn()
    now = datetime.now(TZ_CST)
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    print(f"\n🔮 未来7天客流预测")
    print("-" * 60)

    for i in range(7):
        future = now + timedelta(days=i)
        weekday = future.weekday()
        date_str = future.strftime("%Y-%m-%d")
        day_name = day_names[weekday]

        # 查找同星期几的历史平均
        hist = conn.execute("""
            SELECT AVG(avg_crowd) as avg_c, AVG(max_crowd) as max_c, COUNT(*) as n
            FROM daily_summary
            WHERE weekday = ? AND is_holiday = 0
        """, (weekday,)).fetchone()

        if hist and hist["n"] > 0:
            est_avg = int(hist["avg_c"])
            est_max = int(hist["max_c"])
            confidence = f"基于{hist['n']}天历史"
        else:
            # 无历史数据，用默认值
            base = 26000 if weekday < 5 else 35000
            est_avg = int(base * 0.2)
            est_max = int(base * 0.35)
            confidence = "默认估算"

        marker = "📍" if i == 0 else "  "
        print(f"{marker} {date_str} {day_name}  预估均值:{est_avg:>5}  预估峰值:{est_max:>5}  ({confidence})")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "today":
        show_today()
    elif cmd == "date" and len(sys.argv) > 2:
        show_date(sys.argv[2])
    elif cmd == "weekday" and len(sys.argv) > 2:
        show_weekday(sys.argv[2])
    elif cmd == "holiday":
        show_summary()
    elif cmd == "summary":
        show_summary()
    elif cmd == "forecast":
        forecast()
    else:
        print(__doc__)
