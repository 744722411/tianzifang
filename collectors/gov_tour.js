import { BaseCollector } from './base.js';

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

    // 尝试抓取官方系统
    try {
      const resp = await fetch('https://tourist.whlyj.sh.gov.cn', {
        signal: AbortSignal.timeout(10000),
        headers: { 'User-Agent': 'Mozilla/5.0' },
      });
      if (resp.ok) {
        const text = await resp.text();
        const match = text.match(/田子坊[\s\S]{0,200}?(\d+)/);
        if (match) {
          return [['in_park_count', parseInt(match[1]), '人', 'measured', { source: 'gov_tour' }]];
        }
      }
    } catch {}

    // 降级：基于历史规律估算
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
