import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import shutil
import sys
import queue
from pathlib import Path


def check_ffmpeg():
    """检查 ffmpeg 是否已安装"""
    return shutil.which("ffmpeg") is not None


def get_video_info(video_path):
    """获取视频信息（时长、帧率、分辨率）"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                video_path
            ],
            capture_output=True, text=True
        )
        import json
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                fps_str = stream.get("r_frame_rate", "25/1")
                num, den = fps_str.split("/")
                fps = round(float(num) / float(den), 2)
                duration = float(stream.get("duration", 0))
                width = stream.get("width", 0)
                height = stream.get("height", 0)
                total_frames = int(stream.get("nb_frames", 0))
                if total_frames == 0:
                    total_frames = int(duration * fps)
                return {
                    "fps": fps,
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "total_frames": total_frames
                }
    except Exception:
        pass
    return None


class VideoCutterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频切帧工具")
        self.root.geometry("680x720")
        self.root.resizable(True, True)
        self.root.minsize(680, 700)
        self.root.configure(bg="#1e1e2e")

        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.fps_mode = tk.StringVar(value="original")
        self.custom_fps = tk.StringVar(value="24")
        self.frame_format = tk.StringVar(value="png")
        self.quality = tk.IntVar(value=95)
        self.is_running = False
        self.process = None
        self._msg_queue = queue.Queue()  # 线程安全消息队列

        self._build_ui()
        self._check_env()
        self._poll_queue()  # 启动主线程轮询

    def _check_env(self):
        if not check_ffmpeg():
            self.log("⚠️  未检测到 ffmpeg，请先运行 install.sh 安装依赖", "warn")
        else:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            self.log(f"✅  {version_line}")

    def _build_ui(self):
        COLORS = {
            "bg": "#1e1e2e",
            "card": "#2a2a3e",
            "accent": "#7c6af7",
            "accent2": "#5a9ef8",
            "text": "#cdd6f4",
            "muted": "#6c7086",
            "border": "#45475a",
            "success": "#a6e3a1",
            "warn": "#fab387",
            "error": "#f38ba8",
        }
        self.COLORS = COLORS

        title_frame = tk.Frame(self.root, bg=COLORS["bg"])
        title_frame.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(
            title_frame, text="🎬 视频切帧工具",
            font=("PingFang SC", 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["accent"]
        ).pack(side="left")

        tk.Label(
            title_frame, text="by ffmpeg",
            font=("PingFang SC", 11),
            bg=COLORS["bg"], fg=COLORS["muted"]
        ).pack(side="left", padx=8, pady=4)

        sep = tk.Frame(self.root, bg=COLORS["border"], height=1)
        sep.pack(fill="x", padx=20, pady=4)

        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=20)

        # --- 输入视频 ---
        self._section_label(main, "📁 输入视频")
        input_row = tk.Frame(main, bg=COLORS["bg"])
        input_row.pack(fill="x", pady=(0, 8))

        self.video_entry = tk.Entry(
            input_row, textvariable=self.video_path,
            font=("PingFang SC", 12), bg=COLORS["card"],
            fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", bd=0
        )
        self.video_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self._style_entry(self.video_entry)

        tk.Button(
            input_row, text="选择文件",
            command=self._choose_video,
            font=("PingFang SC", 11),
            bg=COLORS["accent"], fg="white",
            activebackground="#9b8afb",
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
        ).pack(side="right")

        # 视频信息标签
        self.info_label = tk.Label(
            main, text="", font=("PingFang SC", 11),
            bg=COLORS["bg"], fg=COLORS["muted"]
        )
        self.info_label.pack(anchor="w", pady=(0, 6))

        # --- 输出目录 ---
        self._section_label(main, "📂 输出目录")
        out_row = tk.Frame(main, bg=COLORS["bg"])
        out_row.pack(fill="x", pady=(0, 8))

        self.out_entry = tk.Entry(
            out_row, textvariable=self.output_dir,
            font=("PingFang SC", 12), bg=COLORS["card"],
            fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", bd=0
        )
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self._style_entry(self.out_entry)

        tk.Button(
            out_row, text="选择目录",
            command=self._choose_output,
            font=("PingFang SC", 11),
            bg=COLORS["accent2"], fg="white",
            activebackground="#7ab8f9",
            relief="flat", bd=0, padx=12, pady=6, cursor="hand2"
        ).pack(side="right")

        # --- 参数设置 ---
        self._section_label(main, "⚙️  参数设置")
        params_frame = tk.Frame(main, bg=COLORS["card"], padx=14, pady=10)
        params_frame.pack(fill="x", pady=(0, 8))

        # 帧率模式
        fps_row = tk.Frame(params_frame, bg=COLORS["card"])
        fps_row.pack(fill="x", pady=3)
        tk.Label(fps_row, text="帧率模式：", font=("PingFang SC", 12),
                 bg=COLORS["card"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")

        for val, text in [("original", "原始帧率"), ("custom", "自定义"), ("every_n", "每N秒一帧")]:
            tk.Radiobutton(
                fps_row, text=text, variable=self.fps_mode, value=val,
                command=self._on_fps_mode_change,
                font=("PingFang SC", 11),
                bg=COLORS["card"], fg=COLORS["text"],
                selectcolor=COLORS["card"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["accent"]
            ).pack(side="left", padx=8)

        # 自定义帧率/间隔
        fps_custom_row = tk.Frame(params_frame, bg=COLORS["card"])
        fps_custom_row.pack(fill="x", pady=3)
        self.fps_label = tk.Label(fps_custom_row, text="帧率（fps）：",
                                  font=("PingFang SC", 12),
                                  bg=COLORS["card"], fg=COLORS["text"], width=10, anchor="w")
        self.fps_label.pack(side="left")
        self.fps_entry = tk.Entry(fps_custom_row, textvariable=self.custom_fps,
                                  width=8, font=("PingFang SC", 12),
                                  bg=COLORS["bg"], fg=COLORS["text"],
                                  insertbackground=COLORS["text"],
                                  relief="flat", bd=0)
        self.fps_entry.pack(side="left", ipady=4, padx=4)
        self._style_entry(self.fps_entry)
        self.fps_entry.config(state="disabled")

        # 图片格式
        fmt_row = tk.Frame(params_frame, bg=COLORS["card"])
        fmt_row.pack(fill="x", pady=3)
        tk.Label(fmt_row, text="图片格式：", font=("PingFang SC", 12),
                 bg=COLORS["card"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")

        for fmt in ["png", "jpg", "webp"]:
            tk.Radiobutton(
                fmt_row, text=fmt.upper(), variable=self.frame_format, value=fmt,
                command=self._on_format_change,
                font=("PingFang SC", 11),
                bg=COLORS["card"], fg=COLORS["text"],
                selectcolor=COLORS["card"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["accent"]
            ).pack(side="left", padx=8)

        # 画质
        quality_row = tk.Frame(params_frame, bg=COLORS["card"])
        quality_row.pack(fill="x", pady=3)
        tk.Label(quality_row, text="画质（JPG）：", font=("PingFang SC", 12),
                 bg=COLORS["card"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")
        self.quality_scale = ttk.Scale(
            quality_row, from_=1, to=100, orient="horizontal",
            variable=self.quality, length=200,
            command=lambda v: self.quality_val_label.config(text=f"{int(float(v))}%")
        )
        self.quality_scale.pack(side="left", padx=4)
        self.quality_val_label = tk.Label(
            quality_row, text="95%", font=("PingFang SC", 11),
            bg=COLORS["card"], fg=COLORS["accent"]
        )
        self.quality_val_label.pack(side="left")

        # --- 进度 ---
        self._section_label(main, "📊 进度")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main, variable=self.progress_var, maximum=100, length=640
        )
        self.progress_bar.pack(fill="x", pady=(0, 4))

        self.progress_label = tk.Label(
            main, text="", font=("PingFang SC", 11),
            bg=COLORS["bg"], fg=COLORS["muted"]
        )
        self.progress_label.pack(anchor="w")

        # --- 日志 ---
        log_frame = tk.Frame(main, bg=COLORS["card"])
        log_frame.pack(fill="both", expand=True, pady=(6, 8))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_frame, height=6,
            font=("Menlo", 11), bg=COLORS["card"],
            fg=COLORS["text"], insertbackground=COLORS["text"],
            relief="flat", bd=0, wrap="word",
            yscrollcommand=scrollbar.set
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=6)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("warn", foreground=COLORS["warn"])
        self.log_text.tag_config("error", foreground=COLORS["error"])
        self.log_text.tag_config("success", foreground=COLORS["success"])
        self.log_text.tag_config("info", foreground=COLORS["muted"])

        # --- 按钮 ---
        btn_row = tk.Frame(self.root, bg=COLORS["bg"])
        btn_row.pack(pady=(0, 16))

        self.start_btn = tk.Button(
            btn_row, text="▶  开始切帧",
            command=self._start,
            font=("PingFang SC", 13, "bold"),
            bg=COLORS["accent"], fg="white",
            activebackground="#9b8afb",
            relief="flat", bd=0, padx=28, pady=10, cursor="hand2"
        )
        self.start_btn.pack(side="left", padx=8)

        self.stop_btn = tk.Button(
            btn_row, text="⏹  停止",
            command=self._stop,
            font=("PingFang SC", 13),
            bg=COLORS["card"], fg=COLORS["text"],
            activebackground=COLORS["border"],
            relief="flat", bd=0, padx=18, pady=10, cursor="hand2",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=8)

        self.open_btn = tk.Button(
            btn_row, text="📂 打开输出目录",
            command=self._open_output,
            font=("PingFang SC", 13),
            bg=COLORS["card"], fg=COLORS["text"],
            activebackground=COLORS["border"],
            relief="flat", bd=0, padx=18, pady=10, cursor="hand2"
        )
        self.open_btn.pack(side="left", padx=8)

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text,
            font=("PingFang SC", 12, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["muted"]
        ).pack(anchor="w", pady=(8, 2))

    def _style_entry(self, entry):
        entry.config(
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["accent"]
        )

    def _on_fps_mode_change(self):
        mode = self.fps_mode.get()
        if mode == "original":
            self.fps_entry.config(state="disabled")
            self.fps_label.config(text="帧率（fps）：")
        elif mode == "custom":
            self.fps_entry.config(state="normal")
            self.fps_label.config(text="帧率（fps）：")
        else:
            self.fps_entry.config(state="normal")
            self.fps_label.config(text="间隔（秒）：")

    def _on_format_change(self):
        fmt = self.frame_format.get()
        state = "normal" if fmt == "jpg" else "disabled"
        self.quality_scale.config(state=state)

    def _choose_video(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv *.webm *.m4v"),
                ("所有文件", "*.*")
            ]
        )
        if path:
            self.video_path.set(path)
            # 自动设置输出目录
            if not self.output_dir.get():
                default_out = str(Path(path).parent / (Path(path).stem + "_frames"))
                self.output_dir.set(default_out)
            self._load_video_info(path)

    def _load_video_info(self, path):
        if not check_ffmpeg():
            return
        info = get_video_info(path)
        if info:
            duration_str = f"{int(info['duration']//60)}:{int(info['duration']%60):02d}"
            self.info_label.config(
                text=f"  {info['width']}×{info['height']}  |  {info['fps']} fps  |  时长 {duration_str}  |  约 {info['total_frames']} 帧",
                fg=self.COLORS["accent2"]
            )
        else:
            self.info_label.config(text="  无法读取视频信息", fg=self.COLORS["warn"])

    def _choose_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)

    def _start(self):
        if not self.video_path.get():
            messagebox.showwarning("提示", "请先选择视频文件")
            return
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请先选择输出目录")
            return
        if not check_ffmpeg():
            messagebox.showerror("错误", "未找到 ffmpeg，请先运行 install.sh 安装")
            return

        os.makedirs(self.output_dir.get(), exist_ok=True)
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set(0)
        self.progress_label.config(text="")

        thread = threading.Thread(target=self._run_ffmpeg, daemon=True)
        thread.start()

    def _build_ffmpeg_cmd(self):
        video = self.video_path.get()
        out_dir = self.output_dir.get()
        fmt = self.frame_format.get()
        mode = self.fps_mode.get()

        output_pattern = os.path.join(out_dir, f"frame_%06d.{fmt}")
        cmd = ["ffmpeg", "-i", video, "-y"]

        if mode == "original":
            pass  # 不加 vf 过滤，使用原始帧率
        elif mode == "custom":
            fps_val = self.custom_fps.get()
            cmd += ["-vf", f"fps={fps_val}"]
        elif mode == "every_n":
            interval = self.custom_fps.get()
            cmd += ["-vf", f"fps=1/{interval}"]

        if fmt == "jpg":
            cmd += ["-q:v", str(int(101 - self.quality.get()))]
        elif fmt == "png":
            cmd += ["-compression_level", "3"]

        cmd.append(output_pattern)
        return cmd

    def _run_ffmpeg(self):
        import time
        cmd = self._build_ffmpeg_cmd()
        self._msg_queue.put(("log", f"执行命令：{' '.join(cmd)}", "info"))
        self._msg_queue.put(("log", "开始切帧，请稍候..."))

        try:
            info = get_video_info(self.video_path.get())
            total_frames = info["total_frames"] if info else 0
            out_dir = self.output_dir.get()
            fmt = self.frame_format.get()

            # 丢弃 stderr/stdout，避免 pipe buffer 阻塞
            self.process = subprocess.Popen(
                cmd,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )

            # 轮询输出目录文件数量来更新进度，每 0.5 秒一次
            while self.process.poll() is None:
                if not self.is_running:
                    break
                time.sleep(0.5)
                try:
                    count = len([f for f in os.listdir(out_dir) if f.endswith(f".{fmt}")])
                    if total_frames > 0:
                        pct = min(count / total_frames * 100, 99)
                        self._msg_queue.put(("progress", pct, count, total_frames))
                except Exception:
                    pass

            self.process.wait()

            if self.process.returncode == 0 and self.is_running:
                actual = len([f for f in os.listdir(out_dir) if f.endswith(f".{fmt}")])
                self._msg_queue.put(("done", actual))
            elif self.is_running:
                self._msg_queue.put(("error",))

        except Exception as e:
            self._msg_queue.put(("log", f"错误：{e}", "error"))
            self._msg_queue.put(("reset",))

    def _update_progress(self, pct, current, total):
        self.progress_var.set(pct)
        self.progress_label.config(
            text=f"已处理 {current} 帧 / 约 {total} 帧  ({pct:.1f}%)",
            fg=self.COLORS["muted"]
        )

    def _on_done(self, count):
        self.progress_var.set(100)
        self.progress_label.config(
            text=f"✅  完成！共输出 {count} 帧",
            fg=self.COLORS["success"]
        )
        self.log(f"✅  切帧完成！共输出 {count} 帧到：{self.output_dir.get()}", "success")
        self._reset_buttons()

    def _on_error(self):
        self.log("❌  ffmpeg 执行出错，请检查视频文件", "error")
        self._reset_buttons()

    def _reset_buttons(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _stop(self):
        if self.process:
            self.process.terminate()
            self.is_running = False
            self.log("⏹  已停止切帧", "warn")
            self._reset_buttons()

    def _open_output(self):
        out = self.output_dir.get()
        if out and os.path.exists(out):
            subprocess.run(["open", out])
        else:
            messagebox.showinfo("提示", "输出目录不存在，请先切帧")

    def _poll_queue(self):
        """主线程轮询消息队列，安全更新 UI"""
        try:
            while True:
                msg_type, *args = self._msg_queue.get_nowait()
                if msg_type == "log":
                    self._do_log(*args)
                elif msg_type == "progress":
                    self._update_progress(*args)
                elif msg_type == "done":
                    self._on_done(*args)
                elif msg_type == "error":
                    self._on_error()
                elif msg_type == "reset":
                    self._reset_buttons()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def log(self, msg, level="normal"):
        """线程安全的日志方法，任何线程都可以调用"""
        self._msg_queue.put(("log", msg, level))

    def _do_log(self, msg, level="normal"):
        """实际写入 Text widget（只在主线程调用）"""
        tag_map = {
            "warn": "warn",
            "error": "error",
            "success": "success",
            "info": "info",
            "normal": ""
        }
        tag = tag_map.get(level, "")
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")


def main():
    root = tk.Tk()

    # 配置 ttk 样式
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#2a2a3e",
        background="#7c6af7",
        borderwidth=0,
        thickness=8
    )
    style.configure(
        "Horizontal.TScale",
        background="#2a2a3e",
        troughcolor="#45475a",
    )

    app = VideoCutterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
