#!/usr/bin/env python3
"""
BOB信源采集脚本 - GitHub Actions云端版
电脑关机也能自动执行，定时抓取全球资讯RSS
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import re
from email.utils import parsedate_to_datetime

# ==================== RSS Feed配置 ====================

FEEDS = {
    "morning": [
        # (方向, 信源名, RSS URL, 级别)
        ("科技与AI", "TechCrunch", "https://techcrunch.com/feed/", "二级"),
        ("科技与AI", "WIRED", "https://www.wired.com/feed/rss", "二级"),
        ("科技与AI", "Google News AI", "https://news.google.com/rss/search?q=artificial+intelligence+when:2d&hl=en-US&gl=US&ceid=US:en", "二级"),
        ("金融市场", "CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "二级"),
        ("中国出海", "Google News", "https://news.google.com/rss/search?q=China+company+overseas+when:3d&hl=en-US&gl=US&ceid=US:en", "二级"),
        ("消费与数码", "Engadget", "https://www.engadget.com/rss-full.xml", "二级"),
        ("消费与数码", "CNET", "https://www.cnet.com/rss/news/", "二级"),
        ("民生与社会", "BBC", "https://feeds.bbci.co.uk/news/rss.xml", "二级"),
    ],
    "evening": [
        ("科技与AI", "The Verge", "https://www.theverge.com/rss/index.xml", "二级"),
        ("科技与AI", "Ars Technica", "https://arstechnica.com/feed/", "二级"),
        ("科技与AI", "MIT Tech Review", "https://www.technologyreview.com/feed/", "二级"),
        ("金融市场", "CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "二级"),
        ("地缘政治", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "二级"),
        ("消费与数码", "Tom's Hardware", "https://www.tomshardware.com/feeds/all", "二级"),
        ("消费与数码", "Fast Company", "https://www.fastcompany.com/rss", "二级"),
        ("民生与社会", "Guardian", "https://www.theguardian.com/world/rss", "二级"),
    ],
}


def fetch_rss(url, source_name, level, direction):
    """抓取RSS feed并解析"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            xml_data = response.read().decode('utf-8', errors='ignore')

        root = ET.fromstring(xml_data)
        items = []

        # RSS 2.0格式
        for item in root.findall('.//item'):
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            description = (item.findtext('description') or '').strip()
            pub_date = (item.findtext('pubDate') or '').strip()

            if title and link:
                desc_clean = re.sub(r'<[^>]+>', '', description).strip()[:200]
                items.append({
                    'direction': direction,
                    'title': title,
                    'link': link,
                    'description': desc_clean,
                    'pub_date': pub_date,
                    'source': source_name,
                    'level': level,
                })

        # Atom格式
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('.//atom:entry', ns):
            title = (entry.findtext('atom:title', '', ns) or '').strip()
            link_elem = entry.find('atom:link', ns)
            link = link_elem.get('href', '') if link_elem is not None else ''
            summary = (entry.findtext('atom:summary', '', ns) or '').strip()
            pub_date = (entry.findtext('atom:published', '', ns) or entry.findtext('atom:updated', '', ns) or '').strip()

            if title and link:
                desc_clean = re.sub(r'<[^>]+>', '', summary).strip()[:200]
                items.append({
                    'direction': direction,
                    'title': title,
                    'link': link,
                    'description': desc_clean,
                    'pub_date': pub_date,
                    'source': source_name,
                    'level': level,
                })

        return items
    except Exception as e:
        print(f"  [ERROR] {source_name}: {e}")
        return []


def parse_date(date_str):
    """解析各种日期格式"""
    if not date_str:
        return None
    # RFC 2822 (RSS pubDate)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    # ISO 8601 (Atom published/updated)
    try:
        clean = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean)
    except Exception:
        pass
    return None


def is_recent(date_str, days=7):
    """检查日期是否在指定天数内"""
    dt = parse_date(date_str)
    if dt is None:
        return True  # 无法解析日期时默认包含
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return (now - dt).days <= days


def generate_markdown(all_items, collection_time, session):
    """生成latest_sources.md格式"""
    lines = []
    lines.append(f"# 信源缓存（云端自动采集 · {collection_time}）\n")
    lines.append(f"> 采集方式：GitHub Actions云端自动执行（电脑无需开机）")
    lines.append(f"> 采集时段：{session}")
    lines.append(f"> 有效期：7天")
    lines.append(f"> 总条目：{len(all_items)}条\n")

    # 按方向分组
    directions_order = ["科技与AI", "金融市场", "中国出海", "地缘政治", "消费与数码", "民生与社会", "政策与监管"]
    directions = {}
    for item in all_items:
        d = item['direction']
        if d not in directions:
            directions[d] = []
        directions[d].append(item)

    for direction in directions_order:
        items = directions.get(direction, [])
        if not items:
            continue
        lines.append(f"\n## {direction}（{len(items)}条）\n")
        for i, item in enumerate(items[:15], 1):
            lines.append(f"### {i}. {item['title']}")
            lines.append(f"- 摘要：{item['description'][:150]}")
            lines.append(f"- 信源：{item['source']}（{item['level']}）")
            lines.append(f"- 日期：{item['pub_date']}")
            lines.append(f"- URL：{item['link']}\n")

    # 采集日志
    lines.append("\n## 信源采集日志\n")
    lines.append("| # | 信源 | 级别 | 方向 | fetch方式 | 抓取条目 | 采集时间 |")
    lines.append("|---|------|------|------|----------|----------|----------|")
    sources_log = {}
    for item in all_items:
        key = (item['source'], item['level'], item['direction'])
        sources_log[key] = sources_log.get(key, 0) + 1
    for i, ((source, level, direction), count) in enumerate(sources_log.items(), 1):
        lines.append(f"| {i} | {source} | {level} | {direction} | RSS自动 | {count}条 | {collection_time} |")

    return '\n'.join(lines)


def main():
    session = sys.argv[1] if len(sys.argv) > 1 else "morning"
    feeds = FEEDS.get(session, FEEDS["morning"])

    # 北京时间
    tz_beijing = timezone(timedelta(hours=8))
    now = datetime.now(tz_beijing)
    collection_time = now.strftime("%Y-%m-%d %H:%M")

    print(f"=== BOB信源采集 [{session}] {collection_time} ===")
    print(f"Feed数量: {len(feeds)}")

    all_items = []
    for direction, source_name, url, level in feeds:
        print(f"  抓取 {source_name}...")
        items = fetch_rss(url, source_name, level, direction)
        recent_items = [item for item in items if is_recent(item['pub_date'], 7)]
        print(f"    获取 {len(items)} 条, 7日内 {len(recent_items)} 条")
        all_items.extend(recent_items[:20])  # 每个feed最多20条

    print(f"\n总条目: {len(all_items)}")

    # 生成markdown
    md_content = generate_markdown(all_items, collection_time, session)

    # 写入文件
    output_file = "latest_sources.md"
    if session == "evening" and os.path.exists(output_file):
        # 晚间追加
        with open(output_file, 'r') as f:
            existing = f.read()
        evening_md = generate_markdown(all_items, collection_time, session)
        with open(output_file, 'w') as f:
            f.write(existing + "\n\n---\n\n" + evening_md)
    else:
        # 早间覆盖写
        with open(output_file, 'w') as f:
            f.write(md_content)

    print(f"\n已写入 {output_file}")

    # 方向分布统计
    directions = {}
    for item in all_items:
        d = item['direction']
        directions[d] = directions.get(d, 0) + 1
    print("\n方向分布:")
    for d, c in sorted(directions.items(), key=lambda x: -x[1]):
        print(f"  {d}: {c}条")

    # 亮点选题
    print("\n亮点选题（前5条）:")
    for i, item in enumerate(all_items[:5], 1):
        print(f"  {i}. [{item['direction']}] {item['title']}")


if __name__ == "__main__":
    main()
