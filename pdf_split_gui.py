"""PDF 拆分工具 - GUI 版

零依赖 (除了 pypdf),双击即可运行。
"""

import sys
import threading
import time
import traceback
from pathlib import Path
from tkinter import Tk, StringVar, filedialog, messagebox, ttk

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        sys.exit("请先安装依赖: pip install pypdf")


# ---------- 核心逻辑 (与 CLI 版共用同一套解析) ----------

def parse_pages(expr: str, total: int) -> list[int]:
    """把 '1,3,5-7' 解析成 0-based 页码列表,保留顺序,去重。"""
    result: list[int] = []
    seen: set[int] = set()
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            pages = range(start, end + 1)
        else:
            pages = [int(part)]
        for p in pages:
            if p < 1 or p > total:
                raise ValueError(f"页码 {p} 超出范围 (共 {total} 页)")
            if p not in seen:
                seen.add(p)
                result.append(p - 1)
    if not result:
        raise ValueError("未解析到任何页码")
    return result


def split_pdf(input_path: Path, pages_expr: str, output_path: Path) -> list[int]:
    reader = PdfReader(str(input_path))
    total = len(reader.pages)
    indices = parse_pages(pages_expr, total)

    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)
    return [i + 1 for i in indices]


# ---------- GUI ----------

class PdfSplitApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("PDF 拆分工具")
        root.geometry("640x340")
        root.minsize(560, 320)

        self.input_var = StringVar()
        self.pages_var = StringVar()
        self.output_var = StringVar()
        self.status_var = StringVar(value="就绪")
        self.total_pages: int | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # 输入文件
        ttk.Label(frm, text="源 PDF:").grid(row=0, column=0, sticky="e", **pad)
        ttk.Entry(frm, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="浏览...", command=self._pick_input).grid(row=0, column=2, **pad)

        # 页数信息
        self.info_label = ttk.Label(frm, text="", foreground="gray")
        self.info_label.grid(row=1, column=1, sticky="w", padx=10)

        # 页码
        ttk.Label(frm, text="页码:").grid(row=2, column=0, sticky="e", **pad)
        pages_entry = ttk.Entry(frm, textvariable=self.pages_var)
        pages_entry.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)
        ttk.Label(
            frm,
            text="示例: 3   |   5-10   |   1,3,5-7,9",
            foreground="gray",
        ).grid(row=3, column=1, sticky="w", padx=10)

        # 输出
        ttk.Label(frm, text="输出到:").grid(row=4, column=0, sticky="e", **pad)
        ttk.Entry(frm, textvariable=self.output_var).grid(row=4, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="另存为...", command=self._pick_output).grid(row=4, column=2, **pad)
        ttk.Label(
            frm,
            text="留空则默认: <原文件名>_split.pdf",
            foreground="gray",
        ).grid(row=5, column=1, sticky="w", padx=10)

        # 按钮行
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=6, column=0, columnspan=3, pady=(18, 6))
        self.run_btn = ttk.Button(btn_frm, text="开始拆分", command=self._on_run, width=16)
        self.run_btn.pack(side="left", padx=6)
        ttk.Button(btn_frm, text="清空", command=self._reset, width=10).pack(side="left", padx=6)

        # 状态条
        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(8, 3),
        )
        status.pack(fill="x", side="bottom")

    # ----- 事件 -----

    def _pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        self._probe_pdf(Path(path))

    def _pick_output(self) -> None:
        initial = self.output_var.get()
        default_name = ""
        if not initial and self.input_var.get():
            src = Path(self.input_var.get())
            default_name = f"{src.stem}_split.pdf"
        path = filedialog.asksaveasfilename(
            title="保存为",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF 文件", "*.pdf")],
        )
        if path:
            self.output_var.set(path)

    def _probe_pdf(self, path: Path) -> None:
        """选中源文件后,读一下总页数展示给用户,并预填输出路径。"""
        try:
            reader = PdfReader(str(path))
            self.total_pages = len(reader.pages)
            self.info_label.config(text=f"共 {self.total_pages} 页", foreground="#2a7")
        except Exception as e:
            self.total_pages = None
            self.info_label.config(text=f"无法读取: {e}", foreground="#c33")
            return
        if not self.output_var.get():
            self.output_var.set(str(path.with_name(f"{path.stem}_split.pdf")))

    def _reset(self) -> None:
        self.input_var.set("")
        self.pages_var.set("")
        self.output_var.set("")
        self.info_label.config(text="")
        self.status_var.set("就绪")
        self.total_pages = None

    def _on_run(self) -> None:
        src = self.input_var.get().strip()
        pages = self.pages_var.get().strip()
        dst = self.output_var.get().strip()

        if not src:
            messagebox.showwarning("提示", "请选择源 PDF")
            return
        if not Path(src).is_file():
            messagebox.showerror("错误", f"文件不存在:\n{src}")
            return
        if not pages:
            messagebox.showwarning("提示", "请填写页码,例如 1,3,5-7")
            return
        if not dst:
            dst = str(Path(src).with_name(f"{Path(src).stem}_split.pdf"))
            self.output_var.set(dst)

        # 后台线程执行,避免大文件时 UI 卡死
        self.run_btn.config(state="disabled")
        self.status_var.set("正在拆分...")
        threading.Thread(
            target=self._do_split,
            args=(Path(src), pages, Path(dst)),
            daemon=True,
        ).start()

    def _do_split(self, src: Path, pages: str, dst: Path) -> None:
        start = time.perf_counter()
        try:
            written = split_pdf(src, pages, dst)
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.root.after(0, self._on_success, dst, written, elapsed_ms)
        except Exception as e:
            tb = traceback.format_exc()
            self.root.after(0, self._on_failure, e, tb)

    def _on_success(self, dst: Path, written: list[int], elapsed_ms: float) -> None:
        self.run_btn.config(state="normal")
        elapsed_text = self._format_elapsed(elapsed_ms)
        self.status_var.set(f"完成: {dst}  (共 {len(written)} 页, 耗时 {elapsed_text})")
        if messagebox.askyesno(
            "完成",
            f"已生成:\n{dst}\n\n"
            f"实际写入页码: {written}\n"
            f"耗时: {elapsed_text}\n\n"
            "是否打开所在文件夹?",
        ):
            self._open_folder(dst.parent)

    @staticmethod
    def _format_elapsed(ms: float) -> str:
        """把毫秒格式化成易读文本,保留毫秒精度。"""
        if ms < 1000:
            return f"{ms:.2f} ms"
        seconds = ms / 1000
        if seconds < 60:
            return f"{seconds:.3f} s ({ms:.0f} ms)"
        minutes, sec = divmod(seconds, 60)
        return f"{int(minutes)} min {sec:.3f} s ({ms:.0f} ms)"

    def _on_failure(self, err: Exception, tb: str) -> None:
        self.run_btn.config(state="normal")
        self.status_var.set(f"失败: {err}")
        messagebox.showerror("拆分失败", f"{err}\n\n详细:\n{tb}")

    def _open_folder(self, folder: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(folder)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception:
            pass


def main() -> None:
    root = Tk()
    # Windows 高 DPI 稍微清晰一点
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    PdfSplitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
