# BOB信源自动采集系统（云端版）

> 电脑关机也能自动运行。每天北京时间 8:00 和 20:00 自动抓取全球资讯RSS，结果存入 latest_sources.md。

## 工作原理

```
GitHub Actions (云端)          WorkBuddy (本地)
┌─────────────────────┐       ┌──────────────────────┐
│ 8:00 早间采集        │       │ BOB说"撰写文章"       │
│ 20:00 晚间采集       │       │                      │
│                     │       │ 1. WebFetch 从GitHub  │
│ Python脚本抓取RSS    │       │    读取latest_sources │
│ → latest_sources.md │──────→│ 2. 选题+撰写          │
│ → 自动commit        │       │ 3. 输出博文集          │
└─────────────────────┘       └──────────────────────┘
```

## 采集信源（8个/次 × 2次/日 = 16个feed/日）

### 早间（8:00·覆盖美洲隔夜+欧洲早盘+亚洲日间）
| 方向 | 信源 | RSS |
|------|------|-----|
| 科技与AI | TechCrunch | techcrunch.com/feed/ |
| 科技与AI | WIRED | wired.com/feed/rss |
| 科技与AI | Google News AI | news.google.com/rss/search?q=AI |
| 金融市场 | CNBC | cnbc.com/rss |
| 中国出海 | Google News China | news.google.com/rss/search?q=China+overseas |
| 消费与数码 | Engadget | engadget.com/rss-full.xml |
| 消费与数码 | CNET | cnet.com/rss/news/ |
| 民生与社会 | BBC | feeds.bbci.co.uk/news/rss.xml |

### 晚间（20:00·覆盖美洲开盘+欧洲午盘+亚洲收盘）
| 方向 | 信源 | RSS |
|------|------|-----|
| 科技与AI | The Verge | theverge.com/rss/index.xml |
| 科技与AI | Ars Technica | arstechnica.com/feed/ |
| 科技与AI | MIT Tech Review | technologyreview.com/feed/ |
| 金融市场 | CNBC | cnbc.com/rss |
| 地缘政治 | Al Jazeera | aljazeera.com/xml/rss/all.xml |
| 消费与数码 | Tom's Hardware | tomshardware.com/feeds/all |
| 消费与数码 | Fast Company | fastcompany.com/rss |
| 民生与社会 | Guardian | theguardian.com/world/rss |

## 部署步骤（3步）

### Step 1: 生成GitHub Token
1. 打开 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. Note: `bob-collector`
4. 勾选权限: `repo`
5. 生成后复制token

### Step 2: 运行部署脚本
```bash
cd /Users/apple/WorkBuddy/2026-07-20-15-10-37/cloud-collector
python3 deploy.py ghp_你的token
```
脚本自动完成：创建仓库 → 上传文件 → 触发首次采集

### Step 3: 告诉我你的GitHub用户名
我会配置WorkBuddy自动从GitHub读取采集结果。

## 手动触发采集
1. 打开仓库的 Actions 页面
2. 选择 "BOB早间信源采集" 或 "BOB晚间信源采集"
3. 点击 "Run workflow"

## 添加/修改RSS Feed
编辑 `collect_sources.py` 中的 `FEEDS` 字典，添加新的feed：
```python
("方向", "信源名", "RSS_URL", "二级"),
```
然后push到GitHub。

## 本地测试
```bash
python3 collect_sources.py morning   # 测试早间采集
python3 collect_sources.py evening   # 测试晚间采集
```
