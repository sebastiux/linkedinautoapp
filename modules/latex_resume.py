'''
LaTeX resume helper.

Takes tailored LaTeX produced by the AI, writes it to a .tex file and compiles
it to a PDF, so the bot can upload a per-job custom resume.

Two ways to compile (controlled by `latex_compiler` in settings.py):
  - "local":  uses a locally installed engine (xelatex/lualatex).
               Windows: install MiKTeX (https://miktex.org/) -> provides xelatex
  - "online": sends the LaTeX to a free online compiler (no install needed).
               NOTE: this uploads the resume text to a third-party service.
  - "auto":   try local first, fall back to online.

If neither works, generation is skipped and the bot uses the default resume.
'''

import os
import re
import json
import shutil
import subprocess
import urllib.request
import urllib.error

from modules.helpers import print_lg

# Free LaTeX-as-a-service endpoint (LaTeX-On-HTTP). Used for "online"/"auto".
ONLINE_LATEX_URL = "https://latex.ytotech.com/builds/sync"


# Built-in master resume, used when `master_resume_path` does not point to a file.
# Replace this (or point master_resume_path to your own .tex) to change your base CV.
DEFAULT_MASTER_RESUME = r"""% Requires XeLaTeX or LuaLaTeX for compilation

\documentclass[a4paper,10pt]{article}

\usepackage[utf8]{inputenc}
\usepackage{geometry}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{fontawesome5}
\usepackage{hyperref}
\usepackage{multicol}
\usepackage{fancyhdr}
\usepackage{array}
\usepackage{tikz}
\usepackage{tabularx}

\definecolor{primary}{RGB}{33, 103, 165}
\definecolor{secondary}{RGB}{80, 80, 80}
\definecolor{accent}{RGB}{0, 150, 136}

\geometry{
  a4paper,
  left=1.2cm,
  right=1.2cm,
  top=1.0cm,
  bottom=1.5cm,
  footskip=0.5cm
}

\titleformat{\section}
  {\color{primary}\large\bfseries}
  {}{0em}
  {\titlerule[1pt]\vspace{0.2em}}
  [\vspace{0.05em}]

\titleformat{\subsection}
  {\color{secondary}\normalsize\bfseries}
  {}{0em}{}

\hypersetup{
  colorlinks=true,
  urlcolor=accent,
  linkcolor=primary
}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyfoot[C]{\textcolor{secondary}{\footnotesize Page \thepage}}

\newcommand{\cvheader}[4]{
  \begin{center}
    {\large\textbf{\textcolor{primary}{#1}}}\\[0.2em]
    {\small\textcolor{secondary}{#2}}\\[0.1em]
    \textcolor{secondary}{
      \footnotesize\faEnvelope\ \href{mailto:#3}{\footnotesize #3} \quad
      \footnotesize\faPhone\ \href{tel:#4}{\footnotesize #4}
    }\\[0.1em]
    \textcolor{secondary}{
      \footnotesize\faGithub\ \href{https://github.com/sebastiux}{\footnotesize github.com/sebastiux} \quad
      \footnotesize\faGlobe\ \href{https://karuna.com.es}{\footnotesize karuna.com.es}
    }
  \end{center}
}

\newcommand{\customitem}[1]{
  \item[\textcolor{accent}{\footnotesize\faAngleRight}] {\small #1}
}

\newcommand{\dateplace}[2]{
  \hfill\textcolor{secondary}{\textit{#1}} \textbullet\ \textcolor{primary}{#2}
}

\newcommand{\workexperience}[5]{
  \subsection{#1 \dateplace{#2}{#3}}
  \textit{#4}\\[-0.2em]
  \begin{itemize}[leftmargin=*,label={\textcolor{accent}{\footnotesize\faAngleRight}},itemsep=-0.2em,parsep=0em]
    #5
  \end{itemize}
}

\newcommand{\education}[4]{
  \subsection{#1 \dateplace{#2}{#3}}
  \begin{itemize}[leftmargin=*,label={\textcolor{accent}{\footnotesize\faAngleRight}},itemsep=-0.2em,parsep=0em]
    #4
  \end{itemize}
}

\newcommand{\skillcategory}[2]{
  \textbf{\textcolor{secondary}{#1:}} & {\small #2} \\[0.15em]
}

\setlength{\parindent}{0pt}

\begin{document}

\cvheader{Carlos Ortega}{Founder \& AI Solutions Consultant · Technology Strategy}{csoh.sebastian@gmail.com}{+52 7202533388}

\vspace{-0.5em}
\begin{center}
  \textit{\textcolor{secondary}{Founder and technology consultant focused on translating business problems into production-ready AI and software solutions. I lead end-to-end projects --- from client discovery through to delivery --- with experience across EdTech, SaaS and enterprise automation. I combine product vision, technical execution and the coordination of multidisciplinary teams.}}
\end{center}

\begin{center}
  \begin{tikzpicture}
    \fill[primary] (0,0) rectangle (2,0.15);
    \fill[accent] (2.5,0) rectangle (5,0.15);
    \fill[secondary] (5.5,0) rectangle (13,0.15);
  \end{tikzpicture}
\end{center}

\vspace{0.3em}

\section{Executive Summary}

\begin{itemize}[leftmargin=*,label={\textcolor{accent}{\footnotesize\faAngleRight}},itemsep=-0.1em,parsep=0em]
  \customitem{\textbf{Strategy \& Consulting}: Closed and delivered AI consulting engagements above 100,000 MXN, managing the full cycle of discovery, proposal, architecture, execution and handover.}
  \customitem{\textbf{Product Leadership}: Definition of roadmaps, functional scope and delivery priorities for SaaS products and bespoke applications in direct collaboration with business stakeholders.}
  \customitem{\textbf{Team Coordination}: Formation and direction of multidisciplinary freelance teams (development, design, content), with responsibility for delivery standards, working cadences and final quality.}
  \customitem{\textbf{Applied AI for Business}: Design and implementation of LLM-based and automation solutions in EdTech, customer service, digital fitness and internal operations, prioritising measurable impact over technical complexity.}
  \customitem{\textbf{Digital Transformation}: Identification of operational bottlenecks and design of automation solutions focused on reducing manual workload and improving efficiency.}
\end{itemize}

\vspace{0.2em}

\section{Professional Experience}

\workexperience{Founder \& Technology Consultant}{August 2025 -- Present}{Karuna Electronics / KarunaDev}{Mexico City, MX}{
  \customitem{Founded a technology consultancy with three service lines (AI products, IT consulting and integrated hardware solutions), operating with a flexible model of specialised collaborators.}
  \customitem{\textbf{NIO Educational Platform --- AI consulting engagement}: Led the design and delivery of an AI-powered learning platform for an institutional client, including microservices architecture, LLM integration and real-time experience, sized for concurrent use at institutional scale.}
  \customitem{\textbf{NIO Mobile App}: Directed the development of the companion application in React Native, extending the learning experience to mobile devices with participation in live sessions.}
  \customitem{\textbf{CalistenIA}: In-house digital fitness product with AI-generated personalised routines and integration with music services, validated as a case of consumer-facing AI application.}
  \customitem{\textbf{Crickett SaaS}: SaaS product offering configurable chatbots on WhatsApp Business, oriented towards customer service automation for SMEs across multiple sectors.}
  \customitem{Defined internal practices for technology selection, commercial proposals and delivery, ensuring consistency across projects and healthy margins per engagement.}
}

\workexperience{IT \& Automation Lead}{July 2025 -- October 2025}{HGROUP}{Mexico City, MX}{
  \customitem{Led the technology strategy of the IT area within a marketing firm, aligning the digital roadmap with the business's commercial priorities.}
  \customitem{Coordinated the delivery of a portfolio of corporate websites and platforms (React, Next.js) under aggressive deadlines.}
  \customitem{Designed and implemented an automation flow for Shopify inventory management with Python, reducing the recurring operational workload of the commercial team.}
  \customitem{Drafted an IT business plan with return projections for AI-assisted marketing automation initiatives.}
}
\clearpage
\workexperience{IT Intern}{August 2024 -- June 2025}{Bocar}{Mexico City, MX}{
  \customitem{Functional administrator of SAP CONCUR; developed Python automation scripts for the analysis of roles and profiles within the FICO module in SAP Basis.}
  \customitem{Implemented Power Automate flows to optimise the operation of internal support tickets.}
}

\workexperience{Systems Development Intern}{September 2022 -- July 2024}{Grupo Corporativo ALTIDSA}{Toluca, MX}{
  \customitem{Developed ORSApp, a desktop application (Java/MySQL) for the management of indirect operational costs.}
  \customitem{Participated in the assembly and validation of PLC circuits for the Mexico City Z\'ocalo lighting project.}
}

\vspace{0.2em}

\section{Education}

\education{BEng in Mechatronics and Cyber-Physical Systems Engineering}{January 2023 -- December 2026}{Universidad Iberoamericana}{
  \customitem{Relevant areas: Control Systems, Signal Processing, AI Reasoning, Digital Systems, Data Structures, OOP.}
}

\education{Computer Engineering (Online Programme)}{July 2022 -- December 2022}{Politecnico di Milano}{
  \customitem{Intensive programme: Mathematical Analysis, Programming Fundamentals, Electromagnetism.}
}

\education{Russian Language Studies}{September 2021 -- July 2022}{Kazan Aviation Institute}{
  \customitem{Scholarship recipient from the Government of Russia. Winner of the Russian History Olympiad (in Russian).}
}

\section{Capabilities and Technical Stack}

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{5cm}X}
  \skillcategory{Strategy \& Consulting}{Client discovery, project scoping, commercial proposals, product roadmaps, solution architecture, stakeholder management}
  \skillcategory{Leadership \& Execution}{Coordination of freelance teams, definition of delivery standards, sprint planning, technical handover to clients}
  \skillcategory{Applied AI}{LLM integration (xAI Grok, OpenAI), prompt engineering, semantic search, multi-agent systems, AI-driven automation}
  \skillcategory{Product \& Frontend}{React, Next.js, TypeScript, React Native, Tailwind CSS, product experience design}
  \skillcategory{Backend \& Architecture}{Node.js, Python, REST APIs, WebSockets, Redis, Docker, Vercel, Railway, Azure}
  \skillcategory{Data \& Enterprise}{MySQL, PostgreSQL, MongoDB, SAP CONCUR / Basis / FICO, Power Automate}
  \skillcategory{Hardware \& Industrial}{STM32, ESP32, Arduino, FPGA/VHDL, PLC, circuit design}
\end{tabularx}

\vspace{0.3em}

\section{Certifications and Languages}

\begin{multicols}{2}
\textbf{Certifications:}
\begin{itemize}[leftmargin=*,label={\textcolor{accent}{\footnotesize\faAngleRight}},itemsep=0.05em,parsep=0em]
  \customitem{IELTS --- Score: 6.5}
  \customitem{SAP Security Consultant}
  \customitem{SAP FICO Fundamentals}
\end{itemize}

\columnbreak

\textbf{Languages:}
\begin{itemize}[leftmargin=*,label={\textcolor{accent}{\footnotesize\faAngleRight}},itemsep=0.05em,parsep=0em]
  \customitem{Spanish --- Native}
  \customitem{English --- C1 (IELTS 6.5)}
  \customitem{Italian --- B2}
  \customitem{Russian --- B1}
\end{itemize}
\end{multicols}

\end{document}
"""


def find_latex_engine() -> str | None:
    '''Returns the name of a locally available LaTeX engine, or None.'''
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
    '''
    Reads the master LaTeX resume template from `path`. If the file is missing
    or unreadable, falls back to the built-in DEFAULT_MASTER_RESUME so the
    feature works out of the box.
    '''
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        print_lg(f"Master resume template not found at '{path}'. Using the built-in hardcoded template.")
        return DEFAULT_MASTER_RESUME
    except Exception as e:
        print_lg("Could not read master resume template; using the built-in hardcoded template.", e)
        return DEFAULT_MASTER_RESUME


def _compile_local(tex_path: str, out_dir: str, pdf_path: str, engine: str) -> str | None:
    try:
        subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", os.path.basename(tex_path)],
            cwd=out_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
        )
        if os.path.exists(pdf_path):
            return pdf_path
        print_lg("Local LaTeX produced no PDF (likely a syntax error in the generated resume).")
    except Exception as e:
        print_lg("Local LaTeX compilation failed.", e)
    return None


def _compile_online(latex_source: str, pdf_path: str) -> str | None:
    try:
        payload = json.dumps({
            "compiler": "xelatex",
            "resources": [{"main": True, "content": latex_source}],
        }).encode("utf-8")
        req = urllib.request.Request(
            ONLINE_LATEX_URL, data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/pdf"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        if data:
            with open(pdf_path, "wb") as fh:
                fh.write(data)
            if os.path.getsize(pdf_path) > 0:
                return pdf_path
    except urllib.error.HTTPError as e:
        print_lg(f"Online LaTeX compiler rejected the document (HTTP {e.code}). The generated LaTeX may have errors.")
    except Exception as e:
        print_lg("Online LaTeX compilation failed (no internet or service unavailable).", e)
    return None


def compile_resume(latex_source: str, out_dir: str, base_name: str, mode: str = "auto") -> str | None:
    '''
    Writes `latex_source` to `out_dir/base_name.tex` and compiles it to a PDF
    using the chosen `mode` ("auto" | "local" | "online").
    Returns the PDF path on success, or None (bot then uses the default resume).
    '''
    if not latex_source:
        return None
    mode = (mode or "auto").lower()
    os.makedirs(out_dir, exist_ok=True)
    tex_path = os.path.join(out_dir, f"{base_name}.tex")
    pdf_path = os.path.join(out_dir, f"{base_name}.pdf")
    try:
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(latex_source)
    except Exception as e:
        print_lg("Could not write the .tex file.", e)
        return None

    engine = find_latex_engine()

    # Local compilation
    if mode in ("auto", "local"):
        if engine:
            pdf = _compile_local(tex_path, out_dir, pdf_path, engine)
            if pdf:
                return pdf
        elif mode == "local":
            print_lg("No local LaTeX engine (xelatex/lualatex) found. Install MiKTeX/TeX Live, or set latex_compiler = \"online\" / \"auto\". Using default resume.")
            return None
        else:
            print_lg("No local LaTeX engine found; trying the online compiler...")

    # Online compilation (fallback for "auto", or primary for "online")
    if mode in ("auto", "online"):
        print_lg("Compiling resume with the online LaTeX service...")
        pdf = _compile_online(latex_source, pdf_path)
        if pdf:
            print_lg("Online LaTeX compilation succeeded.")
            return pdf

    print_lg("Could not produce a custom PDF; using the default resume.")
    return None
