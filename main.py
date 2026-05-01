#!/usr/bin/env python3
"""
田子坊人流数据采集 - 主入口

用法:
    python main.py              # 采集一次
    python main.py --schedule   # 启动定时采集 (每天4次)
    python main.py --init       # 仅初始化数据库
"""
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta, timezone

from config.settings import COLLECT_HOURS, DB_PATH
from config.db import init_db, get_conn
from collectors.gov_tour import GovTourCollector
from collectors.amap import AmapCollector
from collectors.weather import WeatherCollector
from collectors.holiday import HolidayCollector

TZ_CST = timezone(timedelta(hours=8))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("tianzifang")


def run_collection():
    """执行一次完整的数据采集"""
    now = datetime.now(TZ_CST)
    log.info(f"=== 开始采集 {now.strftime('%Y-%m-%d %H:%M')} ===")

    conn = get_conn()
    collectors = [
        GovTourCollector(),
        WeatherCollector(),
        HolidayCollector(),
    ]

    # 高德地图需要 API Key
    from config.settings import AMAP_API_KEY
    if AMAP_API_KEY:
        collectors.append(AmapCollector())
    else:
        log.warning("AMAP_API_KEY 未设置，跳过高德地图数据采集")

    total = 0
    for c in collectors:
        try:
            records = c.collect()
            count = c.save(conn, records)
            total += count
            log.info(f"  [{c.name}] 采集 {count} 条记录")
        except Exception as e:
            log.error(f"  [{c.name}] 采集失败: {e}")

    conn.close()
    log.info(f"=== 采集完成，共 {total} 条记录 ===")
    return total


def run_daily_summary():
    """每天结束时生成当日汇总"""
    now = datetime.now(TZ_CST)
    date_str = now.strftime("%Y-%m-%d")
    log.info(f"生成 {date_str} 日汇总...")

    conn = get_conn()

    # 查询当天所有在园人数
    rows = conn.execute("""
        SELECT value, ts FROM crowd_data
        WHERE source = 'gov_tour' AND metric = 'in_park_count'
        AND date(ts) = ?
        AND confidence IN ('measured', 'scraped')
        ORDER BY ts
    """, (date_str,)).fetchall()

    if rows:
        values = [r["value"] for r in rows if r["value"] is not None]
        if values:
            max_crowd = int(max(values))
            avg_crowd = round(sum(values) / len(values))
            total_visitors = int(sum(values))  # 粗略累计

            # 找峰值时段
            peak_row = max(rows, key=lambda r: r["value"] or 0)
            peak_hour = int(peak_row["ts"][11:13]) if peak_row["ts"] else None

            # 获取天气
            weather = conn.execute("""
                SELECT value FROM crowd_data
                WHERE source = 'weather' AND metric = 'temperature_max'
                AND date(ts) = ?
                LIMIT 1
            """, (date_str,)).fetchone()
            temp_high = weather["value"] if weather else None

            weather_low = conn.execute("""
                SELECT value FROM crowd_data
                WHERE source = 'weather' AND metric = 'temperature_min'
                AND date(ts) = ?
                LIMIT 1
            """, (date_str,)).fetchone()
            temp_low = weather_low["value"] if weather_low else None

            # 节假日
            holiday = conn.execute("""
                SELECT value, raw_json FROM crowd_data
                WHERE source = 'holiday' AND metric = 'is_holiday'
                AND date(ts) = ?
                LIMIT 1
            """, (date_str,)).fetchone()
            is_holiday = int(holiday["value"]) if holiday else 0

            weekday = now.weekday()

            conn.execute("""
                INSERT OR REPLACE INTO daily_summary
                (date, weekday, is_holiday, temperature_high, temperature_low,
                 max_crowd, avg_crowd, peak_hour, total_visitors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, weekday, is_holiday, temp_high, temp_low,
                  max_crowd, avg_crowd, peak_hour, total_visitors))
            conn.commit()
            log.info(f"  日汇总: 最大{max_crowd}人 均值{avg_crowd}人 峰值{peak_hour}时")
    else:
        log.info(f"  当天无实测数据，跳过汇总")

    conn.close()


def schedule_jobs():
    """设置定时采集任务"""
    for hour in COLLECT_HOURS:
        time_str = f"{hour:02d}:00"
        schedule.every().day.at(time_str).do(run_collection)
        log.info(f"已注册定时任务: 每天 {time_str}")

    # 每天 23:30 生成日汇总
    schedule.every().day.at("23:30").do(run_daily_summary)
    log.info("已注册定时任务: 每天 23:30 生成日汇总")

    log.info("定时任务已启动，Ctrl+C 退出")
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    init_db()

    if "--init" in sys.argv:
        print(f"数据库已初始化: {DB_PATH}")
        return

    if "--schedule" in sys.argv:
        # 先采集一次
        run_collection()
        schedule_jobs()
    else:
        run_collection()


if __name__ == "__main__":
    main()
