#!/bin/zsh
# =============================================
# 视频切帧脚本
# 用法：将视频文件拖到此脚本上，或命令行运行：
#   ./切帧.sh 视频文件 [fps] [格式]
# 示例：
#   ./切帧.sh video.mp4          # 原始帧率，PNG
#   ./切帧.sh video.mp4 8        # 8fps，PNG
#   ./切帧.sh video.mp4 1 jpg    # 1fps，JPG
# =============================================

VIDEO="$1"
FPS="${2:-}"       # 可选，留空则使用原始帧率
FORMAT="${3:-png}" # 可选，默认 png，支持 png/jpg/webp

# 检查参数
if [[ -z "$VIDEO" ]]; then
    echo "❌  请将视频文件拖到此脚本上，或传入视频路径"
    echo "用法：$0 <视频文件> [fps] [格式(png/jpg/webp)]"
    read -r "?按回车键退出..."
    exit 1
fi

if [[ ! -f "$VIDEO" ]]; then
    echo "❌  文件不存在：$VIDEO"
    read -r "?按回车键退出..."
    exit 1
fi

# 检查 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "❌  未找到 ffmpeg，请先运行：brew install ffmpeg"
    read -r "?按回车键退出..."
    exit 1
fi

# 输出目录：当前脚本所在目录下，以视频名命名
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VIDEO_NAME=$(basename "$VIDEO")
STEM="${VIDEO_NAME%.*}"
OUT_DIR="${SCRIPT_DIR}/${STEM}_frames"

mkdir -p "$OUT_DIR"

echo "========================================"
echo "🎬  视频切帧开始"
echo "  输入：$VIDEO"
echo "  输出：$OUT_DIR"
echo "  格式：$(echo $FORMAT | tr 'a-z' 'A-Z')"
if [[ -n "$FPS" ]]; then
    echo "  帧率：${FPS} fps"
else
    echo "  帧率：原始帧率"
fi
echo "========================================"

# 构建 ffmpeg 命令
CMD=(ffmpeg -i "$VIDEO" -y)

if [[ -n "$FPS" ]]; then
    CMD+=(-vf "fps=${FPS}")
fi

if [[ "$FORMAT" == "jpg" ]]; then
    CMD+=(-q:v 2)
elif [[ "$FORMAT" == "png" ]]; then
    CMD+=(-compression_level 3)
fi

CMD+=("${OUT_DIR}/frame_%06d.${FORMAT}")

# 执行
"${CMD[@]}"

if [[ $? -eq 0 ]]; then
    COUNT=$(ls "$OUT_DIR"/*.${FORMAT} 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo "========================================"
    echo "✅  切帧完成！共输出 ${COUNT} 帧"
    echo "📂  保存位置：${OUT_DIR}"
    echo "========================================"
    # 自动用 Finder 打开输出目录
    open "$OUT_DIR"
else
    echo ""
    echo "❌  切帧失败，请检查视频文件是否损坏"
fi

read -r "?按回车键退出..."
