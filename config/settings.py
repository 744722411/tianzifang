"""田子坊人流数据采集 - 配置"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tianzifang.db"

# 田子坊坐标
TIANZIFANG_LNG = 121.4625
TIANZIFANG_LAT = 31.2070

# 高德地图 API Key
AMAP_API_KEY = os.environ.get("AMAP_API_KEY", "")

# 采集时间
COLLECT_HOURS = [8, 12, 16, 20]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
