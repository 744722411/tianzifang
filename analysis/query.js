#!/usr/bin/env node
/**
 * 田子坊人流数据 - 查询工具
 *
 * 用法:
 *   node analysis/query.js today          # 今日数据
 *   node analysis/query.js date 2026-05-01
 *   node analysis/query.js summary         # 数据概览
 *   node analysis/query.js forecast        # 未来7天预测
 */
import { getDb } from '../config/db.js';

const DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

async function showToday() {
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' });
  await showDate(today);
}

async function showDate(dateStr) {
  const db = await getDb();
  console.log(`\n📊 ${dateStr} 田子坊数据`);
  console.log('-'.repeat(50));

  // 在园人数
  const rows = db.exec(`
    SELECT ts, value, confidence FROM crowd_data
    WHERE source = 'gov_tour' AND metric = 'in_park_count' AND ts LIKE '${dateStr}%'
    ORDER BY ts
  `);

  if (rows.length > 0 && rows[0].values.length > 0) {
    console.log(`\n🚶 在园人数 (${rows[0].values.length} 条):`);
    for (const [ts, value, conf] of rows[0].values) {
      const time = ts.substring(11, 16);
      const icon = conf === 'measured' ? '📍' : '📐';
      console.log(`  ${time}  ${icon} ${String(Math.round(value)).padStart(6)} 人`);
    }
  } else {
    console.log('\n🚶 在园人数: 无数据');
  }

  // 天气
  const weather = db.exec(`
    SELECT metric, value, unit FROM crowd_data
    WHERE source = 'weather' AND ts LIKE '${dateStr}%'
  `);
  if (weather.length > 0 && weather[0].values.length > 0) {
    console.log('\n🌤 天气:');
    for (const [metric, value, unit] of weather[0].values) {
      if (metric === 'weather_desc') console.log(`  ${unit}`);
      else console.log(`  ${metric}: ${value}${unit}`);
    }
  }

  // 日汇总
  const summary = db.exec(`SELECT * FROM daily_summary WHERE date = '${dateStr}'`);
  if (summary.length > 0 && summary[0].values.length > 0) {
    const [date, weekday, isHoliday, holidayName, weatherDesc, tempHigh, tempLow, maxCrowd, avgCrowd, peakHour, total] = summary[0].values[0];
    console.log(`\n📈 日汇总:`);
    console.log(`  最大客流: ${maxCrowd} 人`);
    console.log(`  平均客流: ${avgCrowd} 人`);
    console.log(`  峰值时段: ${peakHour}时`);
  }
}

async function showSummary() {
  const db = await getDb();
  console.log('\n📊 数据概览');
  console.log('-'.repeat(40));

  const total = db.exec('SELECT COUNT(*) FROM crowd_data');
  const days = db.exec('SELECT COUNT(*) FROM daily_summary');
  const range = db.exec('SELECT MIN(date), MAX(date) FROM daily_summary');

  console.log(`  总记录数: ${total[0]?.values[0]?.[0] || 0}`);
  console.log(`  日汇总天数: ${days[0]?.values[0]?.[0] || 0}`);
  if (range.length > 0 && range[0].values[0][0]) {
    console.log(`  时间范围: ${range[0].values[0][0]} ~ ${range[0].values[0][1]}`);
  }
}

async function forecast() {
  const db = await getDb();
  const now = new Date();

  console.log('\n🔮 未来7天客流预测');
  console.log('-'.repeat(60));

  for (let i = 0; i < 7; i++) {
    const future = new Date(now);
    future.setDate(future.getDate() + i);
    const dateStr = future.toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' });
    const wd = future.getDay() === 0 ? 6 : future.getDay() - 1;
    const dayName = DAY_NAMES[wd];

    const hist = db.exec(`
      SELECT AVG(avg_crowd), AVG(max_crowd), COUNT(*) FROM daily_summary
      WHERE weekday = ${wd} AND is_holiday = 0
    `);

    let estAvg, estMax, conf;
    if (hist.length > 0 && hist[0].values[0][2] > 0) {
      estAvg = Math.round(hist[0].values[0][0]);
      estMax = Math.round(hist[0].values[0][1]);
      conf = `基于${hist[0].values[0][2]}天历史`;
    } else {
      const base = wd < 5 ? 26000 : 35000;
      estAvg = Math.round(base * 0.2);
      estMax = Math.round(base * 0.35);
      conf = '默认估算';
    }

    const marker = i === 0 ? '📍' : '  ';
    console.log(`${marker} ${dateStr} ${dayName}  均值:${String(estAvg).padStart(5)}  峰值:${String(estMax).padStart(5)}  (${conf})`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || 'summary';

  switch (cmd) {
    case 'today': await showToday(); break;
    case 'date': await showDate(args[1]); break;
    case 'summary': await showSummary(); break;
    case 'forecast': await forecast(); break;
    default: console.log(__doc || 'node analysis/query.js [today|date|summary|forecast]');
  }
}

main().catch(console.error);
