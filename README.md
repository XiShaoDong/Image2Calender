# poster2ics — 图片批量导入苹果日历

网页上传活动海报/截图（多张），自动 OCR 识别并解析出标题、日期、时间、地点，预览确认后合并生成一个 .ics 文件，手机点开即可导入苹果日历。

## 快速开始

```bash
pip install -r requirements.txt
# 获取免费 OCR key: https://ocr.space/ocrapi#freeapi （25,000次/月）
export OCRSPACE_KEY=你的key   # 或在网页设置区粘贴（保存一次永久生效）
# 可选：获取免费 Gemini key: https://aistudio.google.com/apikey （1,500次/天）
export GEMINI_KEY=你的key      # 或在网页设置区粘贴，用于复杂海报的智能解析
uvicorn app:app --port 8000
# 浏览器打开 http://localhost:8000
```

两个 Key 都可以在网页设置区粘贴保存，存到本地 config.json，之后打开页面自动回填，无需重复输入。

## 解析策略

- 规则解析（纯正则，零成本）优先：结构规整的排班表、带"时间：/地点："标签的海报直接解析
- LLM 兜底：正则失败或结果可疑（无日期/无标题/多候选日期）时，自动调 Gemini 智能解析
- 解析来源会显示在卡片上（"智能解析（LLM）"标记），LLM 不可用或失败时自动回退到规则结果

## 手机使用

1. 电脑浏览器上传图片 → 预览确认 → 下载 events.ics
2. AirDrop/微信发送到 iPhone
3. iPhone 点开 events.ics → 添加全部 → 已导入苹果日历

### 一键直通（推荐，手机浏览器直接操作）

1. iPhone 浏览器（任意浏览器均可）打开本服务地址
2. 上传图片 → 预览确认 → 点「生成日历文件」→ 点绿色「在 iPhone 上导入到日历」
3. iOS 直接弹出日历导入界面 → 选择要分配的日历 → 添加全部

本地部署时 iPhone 需与电脑同一 WiFi；云端部署（Render）则随时随地可用。

## 部署到 Render（免费）

1. 将代码推送到 GitHub（见下）
2. 打开 https://render.com → New + → Web Service → 连接 GitHub 仓库
3. 构建命令：`pip install -r requirements.txt`
4. 启动命令：`uvicorn app:app --host 0.0.0.0 --port $PORT`
5. 环境变量：添加 `OCRSPACE_KEY`（必填）、`GEMINI_KEY`（选填）
6. 部署完成后访问 `https://<服务名>.onrender.com`

也可用仓库内的 `render.yaml` 一键部署（Blueprint）。

> 注意：云端部署时网页保存的 key 存在临时磁盘，重启会丢失，请务必在 Render 控制台用环境变量配置两个 key。

## 推送到 GitHub

```bash
cd ~/dev/opencode/poster2ics
git remote add origin git@github.com:你的用户名/poster2ics.git
git push -u origin main
```

## 测试

```bash
pytest -q
```

## 限制

- OCR.space 免费版：单图 ≤1MB（页面自动压缩）、每日 500 次
- 默认未写时间的活动按 0:00 开始、时长 2 小时，可在预览中修改
