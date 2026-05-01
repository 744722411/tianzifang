# 田子坊人流数据采集与分析系统

## 概述
自动采集田子坊区域的人流/客流数据，存储到 SQLite 数据库，支持历史查询和趋势分析。

## 数据源
| 数据源 | 类型 | 频率 | 说明 |
|--------|------|------|------|
| 上海市A级景区实时发布系统 | 政府官方 | 每30分钟 | 田子坊在园人数、舒适度 |
| 高德地图 API | 交通路况 | 每次采集 | 周边拥堵指数，间接反映人流 |
| 天气数据 | 气象 | 每次采集 | 温度、天气状况、是否节假日 |
| 上海公共数据平台 | 政府开放 | 历史补充 | data.sh.gov.cn 文旅数据 |

## 采集频率
每天4次：08:00, 12:00, 16:00, 20:00

## 项目结构
```
tianzifang/
├── config/          # 配置文件
├── collectors/      # 数据采集器
│   ├── gov_tour.py  # 上海景区实时发布系统
│   ├── amap.py      # 高德地图路况
│   ├── weather.py   # 天气数据
│   └── base.py      # 采集器基类
├── analysis/        # 数据分析
│   ├── query.py     # 查询工具
│   └── forecast.py  # 人流预测模型
├── data/            # SQLite 数据库
├── scripts/         # 运维脚本
└── main.py          # 主入口（定时采集）
```

## 快速开始
```bash
pip install -r requirements.txt
python main.py              # 手动采集一次
python main.py --schedule   # 启动定时采集
python analysis/query.py    # 查询历史数据
```
