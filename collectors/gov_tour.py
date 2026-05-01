"""
上海市A级景区实时发布系统 - 数据采集

系统地址: https://tourist.whlyj.sh.gov.cn
数据源: 各景区通过闸机/红外/视频每30分钟上报在园人数
采集方式: 尝试抓取公开接口，如果需要登录则降级为间接采集
"""
import re
import json
from bs4 import BeautifulSoup
from .base import BaseCollector


class GovTourCollector(BaseCollector):
    name = "gov_tour"

    # 已知的上海景区数据接口（从公开页面分析）
    BASE_URL = "https://tourist.whlyj.sh.gov.cn"
    # 备用: 上海发布公开查询页面
    PUBLIC_URL = "https://shanghaicity.openservice.kankanews.com/public/tour"

    def collect(self):
        records = []
        now = self.now()
        hour, minute = now.hour, now.minute

        # 方法1: 尝试直接抓取官方系统
        result = self._try_gov_system()
        if result:
            records.extend(result)

        # 方法2: 尝试上海发布平台
        if not records:
            result = self._try_public_platform()
            if result:
                records.extend(result)

        # 方法3: 降级 - 根据时间段和历史数据估算
        if not records:
            records = self._estimate_from_history(now)

        return records

    def _try_gov_system(self):
        """尝试从官方系统获取数据"""
        try:
            resp = self.fetch(self.BASE_URL, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                # 查找田子坊相关的数据
                text = soup.get_text()
                # 尝试匹配客流数据
                match = re.search(r'田子坊[\s\S]{0,200}?(\d+)', text)
                if match:
                    count = int(match.group(1))
                    return [("in_park_count", count, "人", "measured",
                             {"source": "gov_tour", "raw_text": text[:500]})]
        except Exception as e:
            pass
        return None

    def _try_public_platform(self):
        """尝试从上海发布公开平台获取"""
        try:
            # 上海发布使用的 API (从网页分析得到)
            api_url = "https://shanghaicity.openservice.kankanews.com/public/tour/GetTourData"
            resp = self.fetch(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        name = item.get("name", "")
                        if "田子坊" in name:
                            count = item.get("count", item.get("currentCount", 0))
                            comfort = item.get("comfort", "")
                            return [("in_park_count", count, "人", "measured",
                                     {"source": "public_platform", "comfort": comfort, "raw": item})]
        except Exception:
            pass
        return None

    def _estimate_from_history(self, now):
        """
        降级方案：基于历史规律估算
        数据来源：
        - 工作日日均约2.6万人次 (2025年数据)
        - 周末更高
        - 峰值3.2万/天
        - 巅峰期日均4万
        """
        hour = now.hour
        weekday = now.weekday()  # 0=周一
        month = now.month

        # 不在营业时间 (田子坊一般10:00-22:00)
        if hour < 9 or hour > 22:
            return [("in_park_count", 0, "人", "estimated",
                     {"reason": "outside_business_hours", "hour": hour})]

        # 基础客流系数 (一天中各时段的人流分布)
        time_factor = {
            9: 0.05, 10: 0.15, 11: 0.25, 12: 0.30,
            13: 0.28, 14: 0.30, 15: 0.32, 16: 0.30,
            17: 0.25, 18: 0.20, 19: 0.18, 20: 0.15,
            21: 0.10, 22: 0.05
        }.get(hour, 0.05)

        # 日均客流（基于季节和星期）
        base_daily = 26000  # 工作日基准
        if weekday >= 5:  # 周末
            base_daily = 35000
        # 旅游旺季加成
        if month in [4, 5, 10]:
            base_daily = int(base_daily * 1.2)
        elif month in [7, 8]:
            base_daily = int(base_daily * 1.1)

        estimated = int(base_daily * time_factor)

        return [("in_park_count", estimated, "人", "estimated",
                 {"reason": "historical_model", "base_daily": base_daily,
                  "time_factor": time_factor, "weekday": weekday})]
