# 10月12日 — 全篇样片（106 字幕 → 42 拍）

本目录是 `srt-media-director` Runtime 对 **全篇** SRT 的真实运行产物（非手写示例）。

## 输入
- `examples/run/10月12日.srt` — 106 条字幕，总时长 **4:14.566**

## 运行（真实 Runtime）
```bash
python cli.py examples/run/10月12日.srt --out out/
python runtime/render_video.py --srt examples/run/10月12日.srt --out 10月12日-full.mp4 --fps 12
```

## 产物
| 文件 | 说明 |
|---|---|
| `player.html` | 自包含可播放播放器（Runtime 主交付物）。42 个 beat 全部内联，无外部 JS/CSS/CDN 依赖，双击即可离线播放 |
| `validation-report.json` | 分层校验报告，`status: PASS` |
| `10月12日-full.mp4` | 整片视频：3028 帧 @ 12fps · libx264 · 1280×720 · 内嵌中文软字幕（体积约 15.5 MB，未随本次提交入库） |

## 结果速览
- cue → beat：**106 → 42**
- 时长：**4:14**
- 门禁：`runtime/self_test.py` **8/8 PASS**
- 环境：Python 3.12 + cairosvg + imageio-ffmpeg

> 提示：仓库内 `player.html` 为完整可播放版本；MP4 因体积与二进制上传限制未入库，可在本地按上方命令重新渲染得到。
