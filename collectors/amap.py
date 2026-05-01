"""
高德地图 API - 田子坊周边路况/拥堵指数

免费额度: 5000次/天
申请地址: https://lbs.amap.com
"""
from config.settings import AMAP_API_KEY, TIANZIFANG_LNG, TIANZIFANG_LAT
from .base import BaseCollector


class AmapCollector(BaseCollector):
    name = "amap"

    def collect(self):
        if not AMAP_API_KEY:
            return [("congestion_index", None, "index", "unavailable",
                     {"reason": "no_api_key", "hint": "设置环境变量 AMAP_API_KEY"})]

        records = []

        # 周边路况
        try:
            url = "https://restapi.amap.com/v3/traffic/status/road"
            params = {
                "key": AMAP_API_KEY,
                "name": "泰康路",
                "city": "上海",
                "extensions": "all",
            }
            resp = self.fetch(url, params=params)
            data = resp.json()

            if data.get("status") == "1" and data.get("trafficinfo"):
                info = data["trafficinfo"]
                roads = info.get("roads", [])
                for road in roads:
                    if "田子坊" in road.get("name", "") or "泰康" in road.get("name", ""):
                        congestion = float(road.get("lcodes", [{}])[0].get("congestion", 0)) if road.get("lcodes") else 0
                        records.append(("congestion_index", congestion, "index", "measured",
                                        {"road": road.get("name"), "direction": road.get("direction"),
                                         "speed": road.get("speed"), "raw": road}))

                # 如果没找到具体路段，用整体数据
                if not records:
                    for road in roads[:3]:
                        records.append(("road_congestion", float(road.get("speed", 0)), "km/h", "measured",
                                        {"road": road.get("name"), "raw": road}))
        except Exception as e:
            records.append(("congestion_index", None, "index", "error",
                            {"error": str(e)}))

        # 周边搜索 - 热门POI（估算区域热度）
        try:
            url = "https://restapi.amap.com/v3/place/around"
            params = {
                "key": AMAP_API_KEY,
                "location": f"{TIANZIFANG_LNG},{TIANZIFANG_LAT}",
                "radius": 500,
                "types": "050000",  # 餐饮
                "offset": 25,
                "page": 1,
            }
            resp = self.fetch(url, params=params)
            data = resp.json()
            if data.get("status") == "1":
                count = int(data.get("count", 0))
                records.append(("nearby_poi_count", count, "个", "measured",
                                {"type": "餐饮", "radius": "500m", "raw_count": count}))
        except Exception:
            pass

        return records if records else [("amap_status", 0, "no_data", "unavailable", {"reason": "no_results"})]
