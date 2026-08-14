# poster2ics — 图片批量导入苹果日历

网页上传活动海报/截图（多张），自动 OCR 识别并解析出标题、日期、时间、地点，预览确认后合并生成一个 .ics 文件，手机点开即可导入苹果日历。

## 快速开始

```bash
pip install -r requirements.txt
# 获取免费 OCR key: https://ocr.space/ocrapi#freeapi （25,000次/月）
export OCRSPACE_KEY=你的key   # 或在网页设置区粘贴
uvicorn app:app --port 8000
# 浏览器打开 http://localhost:8000
```

## 手机使用

1. 电脑浏览器上传图片 → 预览确认 → 下载 events.ics
2. AirDrop/微信发送到 iPhone
3. iPhone 点开 events.ics → 添加全部 → 已导入苹果日历

（同一 WiFi 下手机也可直接访问 http://电脑IP:8000）

## 测试

```bash
pytest -q
```

## 限制

- OCR.space 免费版：单图 ≤1MB（页面自动压缩）、每日 500 次
- 默认未写时间的活动按 0:00 开始、时长 2 小时，可在预览中修改
