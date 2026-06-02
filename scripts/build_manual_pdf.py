"""MANUAL.md → MANUAL.pdf 변환 스크립트.

사용법:
    python scripts/build_manual_pdf.py

요구사항:
    - markdown
    - weasyprint
"""
from pathlib import Path
import markdown
from weasyprint import HTML, CSS

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH  = BASE_DIR / 'MANUAL.md'
PDF_PATH = BASE_DIR / 'MANUAL.pdf'


CSS_TEXT = """
@page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-family: 'Noto Sans CJK KR', 'Apple SD Gothic Neo', 'NanumGothic', sans-serif;
        font-size: 9pt;
        color: #666;
    }
}
body {
    font-family: 'Noto Sans CJK KR', 'Apple SD Gothic Neo', 'NanumGothic', 'Malgun Gothic', sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #222;
}
h1 {
    font-size: 22pt;
    color: #1a6b3c;
    border-bottom: 3px solid #1a6b3c;
    padding-bottom: 8px;
    margin-top: 0;
    page-break-before: avoid;
}
h2 {
    font-size: 15pt;
    color: #2d9e5f;
    border-left: 5px solid #2d9e5f;
    padding-left: 10px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
}
h3 {
    font-size: 12pt;
    color: #1565c0;
    margin-top: 18px;
    margin-bottom: 8px;
    page-break-after: avoid;
}
h4 {
    font-size: 11pt;
    color: #444;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
}
p { margin: 6px 0; }
ul, ol { margin: 6px 0 10px 18px; padding-left: 8px; }
li { margin: 3px 0; }
strong { color: #1a6b3c; }
code {
    background: #f5f5f5;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 9.5pt;
    font-family: Menlo, Consolas, monospace;
    color: #c62828;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 10pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #d0d0d0;
    padding: 6px 9px;
    text-align: left;
    vertical-align: top;
}
th {
    background: #f0f4f8;
    font-weight: 700;
    color: #1a6b3c;
}
blockquote {
    border-left: 4px solid #f57c00;
    background: #fff8e1;
    padding: 8px 14px;
    margin: 10px 0;
    color: #5d4037;
    font-size: 10pt;
}
hr {
    border: none;
    border-top: 1px dashed #ccc;
    margin: 22px 0;
}
em { color: #888; }
a { color: #1565c0; text-decoration: none; }
"""

def main():
    md_text = MD_PATH.read_text(encoding='utf-8')
    html_body = markdown.markdown(
        md_text,
        extensions=['extra', 'sane_lists', 'toc'],
    )
    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>용산어린이정원 사용 매뉴얼</title></head>
<body>{html_body}</body></html>"""
    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(
        str(PDF_PATH),
        stylesheets=[CSS(string=CSS_TEXT)],
    )
    print(f'생성 완료: {PDF_PATH}')


if __name__ == '__main__':
    main()
