# 视频切帧工具

基于 `ffmpeg` 的视频逐帧提取脚本，将视频拆分为图片序列，用于后续风格化处理。

---

## 环境要求

- macOS
- ffmpeg（未安装请运行：`brew install ffmpeg`）

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `切帧.sh` | 命令行切帧脚本（主工具） |
| `install.sh` | 一键安装依赖脚本 |

---

## 快速开始

### 安装依赖（首次使用）

```bash
./install.sh
```

### 基本用法

```bash
./切帧.sh <视频文件> [fps] [格式]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `视频文件` | 视频路径（必填） | — |
| `fps` | 输出帧率，留空则使用视频原始帧率 | 原始帧率 |
| `格式` | 图片格式：`png` / `jpg` / `webp` | `png` |

---

## 使用示例

```bash
# 提取所有帧（原始帧率，PNG 格式）
./切帧.sh video.mp4

# 每秒提取 8 帧（PNG）
./切帧.sh video.mp4 8

# 每秒提取 1 帧（适合长视频采样）
./切帧.sh video.mp4 1

# 每秒提取 24 帧，保存为 JPG
./切帧.sh video.mp4 24 jpg

# 使用完整路径
./切帧.sh "/Users/rick/Downloads/my_video.mp4" 30 png
```

---

## 输出位置

输出目录自动创建在**视频文件的同级目录**下，命名规则为：

```
视频文件名_frames/
```

例如：

```
~/Downloads/my_video.mp4
~/Downloads/my_video_frames/
├── frame_000001.png
├── frame_000002.png
├── frame_000003.png
└── ...
```

切帧完成后会自动用 Finder 打开输出目录。

---

## 图片格式对比

| 格式 | 特点 | 适用场景 |
|------|------|----------|
| `png` | 无损压缩，文件较大 | 需要最高画质时（默认推荐） |
| `jpg` | 有损压缩，文件小 | 存储空间有限时 |
| `webp` | 有损/无损，体积最小 | 需要平衡画质与体积时 |

---

## 常见问题

**Q：切帧速度很慢？**
A：PNG 编码较慢，改用 JPG 可显著提速：
```bash
./切帧.sh video.mp4 "" jpg
```

**Q：帧数太多，硬盘不够？**
A：降低提取帧率，例如每秒只取 4 帧：
```bash
./切帧.sh video.mp4 4
```

**Q：提示"未找到 ffmpeg"？**
A：运行 `brew install ffmpeg` 安装，或执行 `./install.sh`。

---

## 后续工作流

```
视频
 ↓  ./切帧.sh
帧图片序列（frame_000001.png ...）
 ↓  AI 风格化（Stable Diffusion / ComfyUI）
风格化图片序列
 ↓  ffmpeg 合成
风格化视频
```

合成命令参考：
```bash
# 将帧序列合成为视频（24fps）
ffmpeg -r 24 -i "frames/frame_%06d.png" -c:v libx264 -pix_fmt yuv420p output.mp4

# 合成时保留原视频音轨
ffmpeg -r 24 -i "frames/frame_%06d.png" -i original.mp4 -map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p output.mp4
```
