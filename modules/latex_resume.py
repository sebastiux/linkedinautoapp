'''
LaTeX resume helper.

Takes tailored LaTeX produced by the AI, writes it to a .tex file and compiles
it to a PDF with XeLaTeX/LuaLaTeX, so the bot can upload a per-job custom resume.

Requires a LaTeX engine installed and on PATH:
  - Windows: MiKTeX (https://miktex.org/)  -> provides `xelatex`
  - macOS:   MacTeX
  - Linux:   TeX Live (texlive-xetex)
If no engine is found, generation is skipped gracefully and the bot falls back
to the default resume.
'''

import os
import re
import shutil
import subprocess

from modules.helpers import print_lg


def find_latex_engine() -> str | None:
    '''Returns the name of an available LaTeX engine, or None.'''
    for engine in ("xelatex", "lualatex"):
        if shutil.which(engine):
            return engine
    return None


def extract_latex(text: str) -> str | None:
    '''
    Pulls the LaTeX document out of an AI response (in case it wrapped it in
    markdown fences or added stray text). Returns None if nothing usable.
    '''
    if not text or not isinstance(text, str):
        return None
    match = re.search(r"\\documentclass[\s\S]*?\\end\{document\}", text)
    if match:
        return match.group(0)
    stripped = text.strip().strip("`")
    return stripped if "\\documentclass" in stripped else None


def load_master_resume(path: str) -> str | None:
    '''Reads the master LaTeX resume template, or returns None if missing.'''
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        print_lg(f"Master resume template not found at '{path}'. Custom resume generation is disabled.")
        return None
    except Exception as e:
        print_lg("Could not read master resume template.", e)
        return None


def compile_resume(latex_source: str, out_dir: str, base_name: str) -> str | None:
    '''
    Writes `latex_source` to `out_dir/base_name.tex` and compiles it to a PDF.
    Returns the PDF path on success, or None (falls back to default resume).
    '''
    if not latex_source:
        return None
    engine = find_latex_engine()
    if not engine:
        print_lg("No LaTeX engine (xelatex/lualatex) found on PATH. Install MiKTeX (Windows) or TeX Live to enable custom resumes. Using the default resume for now.")
        return None

    os.makedirs(out_dir, exist_ok=True)
    tex_path = os.path.join(out_dir, f"{base_name}.tex")
    pdf_path = os.path.join(out_dir, f"{base_name}.pdf")
    try:
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(latex_source)
        subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", tex_path],
            cwd=out_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
        )
        if os.path.exists(pdf_path):
            return pdf_path
        print_lg("LaTeX compilation produced no PDF (likely a syntax error in the generated resume). Using the default resume.")
        return None
    except Exception as e:
        print_lg("LaTeX compilation failed. Using the default resume.", e)
        return None
