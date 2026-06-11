# GitHub 热榜 (Trending Viewer)

一个能查看 GitHub 每日 / 每周 / 每月热门开源项目的网页,每条项目都附带**中文翻译介绍**,按 star 数排序。

**完全部署在 GitHub 内部** —— GitHub Actions 每小时抓取并翻译一次,产物提交到仓库,GitHub Pages 直接托管静态页面。零服务器、零费用、零第三方。

- 抓取: Python + httpx + BeautifulSoup
- 翻译: Google Translate (经 `deep-translator`)
- 前端: 原生 HTML + CSS + JS,GitHub 暗色风格
- 自动化: GitHub Actions (cron `0 * * * *`)

## 部署到 GitHub Pages (5 分钟)

### 1. 创建 GitHub 仓库

在 GitHub 新建一个公开仓库,例如 `github-trending`(名字自定,影响最终 URL)。

### 2. 推送代码

```bash
cd github-trending
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的用户名>/github-trending.git
git push -u origin main
```

### 3. 启用 GitHub Pages

- 进入仓库的 **Settings → Pages**
- **Source** 选择 `Deploy from a branch`
- **Branch** 选 `main` / `(root)`(直接用仓库根目录,前端在 `static/` 子目录里)

> ⚠️ 关键: GitHub Pages 默认从根目录托管。如果你想让访问 URL 就是 `https://<user>.github.io/<repo>/`,根目录里就需要 `index.html`。本项目把 `index.html` 放在 `static/` 下,所以推荐:
>
> - **方案 A (推荐)**: 把 `static/index.html`、`static/style.css`、`static/app.js`、`static/data/` 里的内容直接放到仓库根 `index.html`、`style.css`、`app.js`、`data/` 下,在 `Settings → Pages` 选 `main` / `root`。
> - **方案 B**: 不动文件结构,GitHub Pages 仍然可以托管 `static/` 目录的内容,选 `main` / `static`,访问 URL 是 `https://<user>.github.io/<repo>/`,一切正常工作。

**(A、B 任选一种,后者更省事)**

### 4. 首次手动触发数据生成

部署好页面后,首次数据还没生成(需要等 1 小时 cron 或者手动触发):

- 进入仓库 **Actions** 页
- 选 `Update Trending Data` workflow
- 点 `Run workflow` → 选 main 分支 → 绿色按钮
- 等待 30-60 秒跑完,会看到一个新的 commit 提交到 `static/data/`

### 5. 打开页面

**方案 A** (文件放根目录): `https://<user>.github.io/`
**方案 B** (文件在 `static/`): `https://<user>.github.io/<repo>/`

之后每小时 GitHub Actions 会自动刷新数据,你只需打开链接即可。

## 本地开发

如果你想改前端或者本地先调试:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

pip install -r build_requirements.txt
python scripts/build_data.py    # 生成 static/data/trending-*.json

# 起一个简单的 http server 就能看
cd static
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

## 目录结构

```
github-trending/
├── app/                      # Python 抓取 + 翻译 (build_data.py 引用)
│   ├── __init__.py
│   ├── scraper.py
│   ├── translator.py
│   └── cache.py
├── scripts/
│   └── build_data.py         # 抓取 + 翻译 → 写 static/data/*.json
├── static/                   # GitHub Pages 托管的目录
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/                 # ← 自动生成的 JSON 在这里
│       ├── trending-daily.json
│       ├── trending-weekly.json
│       ├── trending-monthly.json
│       └── manifest.json
├── .github/
│   └── workflows/
│       └── update.yml        # 每小时 cron + 手动触发
├── build_requirements.txt    # build 阶段需要的 Python 依赖
├── requirements.txt          # 老版 FastAPI 后端依赖 (本地调试用,可选)
├── app/main.py               # 老版 FastAPI 后端 (本地调试用,可选)
├── run.py                    # 老版启动脚本 (本地调试用,可选)
└── README.md
```

> 注: `app/main.py` / `run.py` / `requirements.txt` 是初版的 FastAPI 后端,**部署到 GitHub Pages 不需要它们**,可以保留作为本地二次开发的参考。

## 常见问题

**Q: Actions 跑失败 / 数据没更新?**
看仓库 **Actions** 页面,点进对应的运行查看日志。Google Translate 偶尔会被限流,workflow 已配置为单个周期失败不影响其他周期。

**Q: 想换翻译服务 (如 DeepL、百度)?**
编辑 `app/translator.py`,把 `GoogleTranslator` 换掉,再 push,Actions 会自动用新翻译器。

**Q: 想更频繁地更新 (例如每 10 分钟)?**
编辑 `.github/workflows/update.yml` 的 `cron`:
```yaml
- cron: "*/10 * * * *"
```
免费账户每月有 2000 分钟额度,每小时跑一次约 1 分钟,完全够用。

**Q: 想自定义 tab 或排序?**
编辑 `static/app.js`,数据已经按 GitHub 原始顺序(本期 star 增量降序)给你了。
