#!/bin/zsh
# 视频切帧工具 - 依赖安装脚本

echo "🎬 视频切帧工具 - 依赖安装"
echo "================================"

# 检查 Homebrew
if ! command -v brew &>/dev/null; then
    echo "⚠️  未检测到 Homebrew，正在安装..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅  Homebrew 已安装"
fi

# 安装 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "📦  正在安装 ffmpeg..."
    brew install ffmpeg
    echo "✅  ffmpeg 安装完成"
else
    echo "✅  ffmpeg 已安装：$(ffmpeg -version 2>&1 | head -1)"
fi

# 检查 Python3
if command -v python3 &>/dev/null; then
    echo "✅  Python3：$(python3 --version)"
else
    echo "❌  未检测到 Python3，请安装 Python 3.8+"
    exit 1
fi

# 检查 tkinter（macOS 系统 Python 自带）
if python3 -c "import tkinter" &>/dev/null; then
    echo "✅  tkinter 已可用"
else
    echo "⚠️  tkinter 不可用，尝试安装 python-tk..."
    brew install python-tk
fi

echo ""
echo "================================"
echo "✅  所有依赖安装完成！"
echo "🚀  运行以下命令启动工具："
echo "    python3 video_cutter.py"
echo "================================"
