import { BaseCollector } from './base.js';

const TOURIST_API = 'https://tourist.whlyj.sh.gov.cn/api/statistics/getViewTourist';
const TIANZIFANG_NAMES = ['上海田子坊景区', '田子坊'];

export class GovTourCollector extends BaseCollector {
  constructor() {
    super();
    this.name = 'gov_tour';
  }

  async collect() {
    const now = new Date();
    const hour = parseInt(now.toLocaleTimeString('en-US', { timeZone: 'Asia/Shanghai', hour12: false, hour: '2-digit' }));
    const weekday = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' })).getDay();
    const month = now.toLocaleDateString('en-US', { timeZone: 'Asia/Shanghai', month: 'numeric' }) * 1;
    const wd = weekday === 0 ? 6 : weekday - 1;

    // 官方数据源：上海市A级景区实时发布系统。
    // 页面实际调用 /api/statistics/getViewTourist，返回全市A级景区实时客流；
    // 其中田子坊记录 NAME=上海田子坊景区，字段 NUM=在园人数，MAX_NUM=瞬时最大承载量，SSD=舒适度。
    try {
      const resp = await fetch(TOURIST_API, {
        signal: AbortSignal.timeout(15000),
        headers: {
          'User-Agent': 'Mozilla/5.0',
          'Accept': 'application/json',
          'Referer': 'https://tourist.whlyj.sh.gov.cn/MobileWebSite/Tourist_Main.html',
        },
      });

      if (resp.ok) {
        const data = await resp.json();
        const rows = Array.isArray(data?.rows) ? data.rows : [];
        const spot = rows.find(r => TIANZIFANG_NAMES.some(name => String(r.NAME || '').includes(name)));
        if (spot && spot.NUM !== undefined && spot.NUM !== null) {
          return [[
            'in_park_count',
            Number(spot.NUM),
            '人',
            'measured',
            {
              source: 'sh_a_scenic_realtime',
              api: TOURIST_API,
              code: spot.CODE,
              name: spot.NAME,
              time: spot.TIME,
              grade: spot.GRADE,
              comfort: spot.SSD,
              max_num: spot.MAX_NUM,
              type: spot.TYPE,
              district: spot.DNAME,
            },
          ]];
        }
      }
    } catch (e) {
      // 失败时进入估算降级，避免采集中断。
    }

    // 降级：基于历史规律估算。官方接口失效时仍保留连续样本，但 confidence 会标注为 estimated。
    if (hour < 9 || hour > 22) {
      return [['in_park_count', 0, '人', 'estimated', { reason: 'outside_business_hours', hour }]];
    }

    const timeFactor = {
      9: 0.05, 10: 0.15, 11: 0.25, 12: 0.30, 13: 0.28, 14: 0.30,
      15: 0.32, 16: 0.30, 17: 0.25, 18: 0.20, 19: 0.18, 20: 0.15,
      21: 0.10, 22: 0.05,
    }[hour] || 0.05;

    let baseDaily = wd < 5 ? 26000 : 35000;
    if ([4, 5, 10].includes(month)) baseDaily = Math.round(baseDaily * 1.2);
    else if ([7, 8].includes(month)) baseDaily = Math.round(baseDaily * 1.1);

    const estimated = Math.round(baseDaily * timeFactor);

    return [
      ['in_park_count', estimated, '人', 'estimated', { reason: 'historical_model', base_daily: baseDaily, time_factor: timeFactor, weekday: wd }],
    ];
  }
}
