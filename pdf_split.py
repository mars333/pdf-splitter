"""
PDF 拆分工具

用法:
    python pdf_split.py <input.pdf> <pages> [output.pdf]

pages 语法:
    单页:     3
    范围:     5-10
    组合:     1,3,5-7,9

示例:
    python pdf_split.py book.pdf 1,3,5-7 out.pdf
    python pdf_split.py book.pdf 5-10
"""

import argparse
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        sys.exit("请先安装依赖: pip install pypdf")


def parse_pages(expr: str, total: int) -> list[int]:
    """把 '1,3,5-7' 解析成 0-based 的页码列表,保留顺序,去重。"""
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


def split_pdf(input_path: Path, pages_expr: str, output_path: Path) -> None:
    reader = PdfReader(str(input_path))
    total = len(reader.pages)
    indices = parse_pages(pages_expr, total)

    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        writer.write(f)

    print(f"已生成: {output_path}  (共 {len(indices)} 页: {[i+1 for i in indices]})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="按指定页码拆分 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="页码示例: 1,3,5-7,9",
    )
    parser.add_argument("input", type=Path, help="输入 PDF 文件")
    parser.add_argument("pages", help="页码表达式,如 1,3,5-7")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="输出 PDF (默认: <原名>_split.pdf)",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        sys.exit(f"文件不存在: {args.input}")

    output = args.output or args.input.with_name(f"{args.input.stem}_split.pdf")

    try:
        split_pdf(args.input, args.pages, output)
    except ValueError as e:
        sys.exit(f"错误: {e}")


if __name__ == "__main__":
    main()
