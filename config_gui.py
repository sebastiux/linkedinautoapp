'''
LinkedIn Auto Job Applier - Configuration GUI

A Tkinter interface to fill in all your profile, CV and search information and
launch the bot, instead of hand-editing the files inside /config.

It reads the current values from the config files, lets you edit every setting
across tabs, writes them back (preserving the helpful inline comments), and can
start/stop runAiBot.py - all from one window.

Run it on your OWN computer (it needs a screen + Chrome) with:
    python config_gui.py

Requires Tkinter (bundled with Python on Windows/macOS; on Debian/Ubuntu:
    sudo apt install python3-tk
).
'''

import os
import re
import ast
import sys
import queue
import threading
import subprocess

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(HERE, "config")

FILES = {
    "personals": os.path.join(CONFIG_DIR, "personals.py"),
    "questions": os.path.join(CONFIG_DIR, "questions.py"),
    "search":    os.path.join(CONFIG_DIR, "search.py"),
    "secrets":   os.path.join(CONFIG_DIR, "secrets.py"),
    "settings":  os.path.join(CONFIG_DIR, "settings.py"),
}


# --------------------------------------------------------------------------- #
# Read / write helpers (comment-preserving, quote-aware)
# --------------------------------------------------------------------------- #
def _split_value_comment(rhs: str):
    '''
    Splits the right-hand side of an assignment into (value, comment).
    `comment` keeps its leading whitespace and the `#`. A `#` inside a string
    literal is correctly ignored.
    '''
    in_str = None
    for i, ch in enumerate(rhs):
        if in_str:
            if ch == in_str and rhs[i - 1] != "\\":
                in_str = None
        else:
            if ch in "'\"":
                in_str = ch
            elif ch == "#":
                j = i
                while j > 0 and rhs[j - 1] in " \t":
                    j -= 1
                return rhs[:j].rstrip(), rhs[j:]
    return rhs.rstrip(), ""


def read_value(content: str, var: str, multiline: bool):
    '''
    Returns the current Python value of `var` found in `content`, or None.
    '''
    if multiline:
        m = re.search(
            r'(?ms)^[ \t]*' + re.escape(var) +
            r'[ \t]*=[ \t]*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')',
            content,
        )
        if not m:
            return None
        try:
            return ast.literal_eval(m.group(1))
        except Exception:
            return None

    m = re.search(r'(?m)^[ \t]*' + re.escape(var) + r'[ \t]*=[ \t]*(.+?)[ \t]*$', content)
    if not m:
        return None
    value_str, _ = _split_value_comment(m.group(1))
    try:
        return ast.literal_eval(value_str)
    except Exception:
        return value_str


def set_value(content: str, var: str, literal: str, multiline: bool) -> str:
    '''
    Replaces the value of `var` in `content` with `literal`, keeping any inline
    comment. Returns the updated content.
    '''
    if multiline:
        pat = re.compile(
            r'(?ms)^([ \t]*' + re.escape(var) +
            r'[ \t]*=[ \t]*)("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'
        )
        return pat.sub(lambda m: m.group(1) + literal, content, count=1)

    pat = re.compile(r'(?m)^([ \t]*' + re.escape(var) + r'[ \t]*=[ \t]*)(.*)$')

    def repl(m):
        _, comment = _split_value_comment(m.group(2))
        return m.group(1) + literal + comment

    return pat.sub(repl, content, count=1)


def _dq(s: str) -> str:
    '''Double-quoted Python string literal for `s`.'''
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_literal(value, vtype: str) -> str:
    '''Builds the Python source literal for `value` of the given `vtype`.'''
    if vtype in ("str", "choice"):
        return _dq("" if value is None else value)
    if vtype == "int":
        try:
            return str(int(str(value).strip()))
        except Exception:
            return "0"
    if vtype == "bool":
        return "True" if value else "False"
    if vtype in ("list", "multichoice"):
        items = value if isinstance(value, list) else \
            [x.strip() for x in str(value).split(",") if x.strip()]
        return "[" + ", ".join(_dq(x) for x in items) + "]"
    if vtype == "text":
        return '"""\n' + str(value).strip("\n") + '\n"""'
    return _dq(value)


# --------------------------------------------------------------------------- #
# Field schema  ->  one tab per config file
# --------------------------------------------------------------------------- #
def F(var, label, vtype, options=None, help="", multiline=False):
    return {"var": var, "label": label, "type": vtype,
            "options": options or [], "help": help, "multiline": multiline}


SCHEMA = [
    ("Personal", "personals", [
        F("first_name",  "First name", "str"),
        F("middle_name", "Middle name", "str", help='Leave empty as "" if none'),
        F("last_name",   "Last name", "str"),
        F("phone_number", "Phone number", "str", help="A valid 10-digit number"),
        F("current_city", "Current city", "str",
          help="If empty, the bot uses the job's location"),
        F("street",  "Street", "str"),
        F("state",   "State", "str"),
        F("zipcode", "Zip code", "str"),
        F("country", "Country", "str"),
        F("ethnicity", "Ethnicity / race", "choice",
          ["Decline", "Hispanic/Latino", "American Indian or Alaska Native",
           "Asian", "Black or African American",
           "Native Hawaiian or Other Pacific Islander", "White", "Other"]),
        F("gender", "Gender", "choice", ["Decline", "Male", "Female", "Other", ""]),
        F("disability_status", "Disability status", "choice", ["Decline", "Yes", "No"]),
        F("veteran_status", "Veteran status", "choice", ["Decline", "Yes", "No"]),
    ]),

    ("Application / CV", "questions", [
        F("default_resume_path", "Default resume (PDF)", "str",
          help="Path to your CV that gets uploaded", multiline=False),
        F("years_of_experience", "Years of experience", "str"),
        F("require_visa", "Need visa sponsorship?", "choice", ["No", "Yes"]),
        F("website", "Portfolio / website", "str"),
        F("linkedIn", "LinkedIn profile URL", "str"),
        F("us_citizenship", "Citizenship status", "choice",
          ["U.S. Citizen/Permanent Resident",
           "Non-citizen allowed to work for any employer",
           "Non-citizen allowed to work for current employer",
           "Non-citizen seeking work authorization",
           "Canadian Citizen/Permanent Resident", "Other", ""]),
        F("desired_salary", "Desired salary (number only)", "int"),
        F("current_ctc", "Current CTC / salary (number only)", "int"),
        F("notice_period", "Notice period (days)", "int"),
        F("recent_employer", "Most recent employer", "str"),
        F("confidence_level", "Confidence level (1-10)", "str"),
        F("linkedin_headline", "LinkedIn headline", "str"),
        F("linkedin_summary", "Professional summary", "text", multiline=True,
          help="A few lines about you (great place to paste a CV summary)"),
        F("cover_letter", "Cover letter", "text", multiline=True),
        F("user_information_all", "Full CV / info (used by AI)", "text", multiline=True,
          help="Paste your whole CV here; AI uses it to answer questions"),
        F("pause_before_submit", "Pause before every submit", "bool"),
        F("pause_at_failed_question", "Pause on unanswerable question", "bool"),
        F("overwrite_previous_answers", "Overwrite previous answers", "bool"),
    ]),

    ("Job Search", "search", [
        F("search_terms", "Search terms (comma separated)", "list",
          help='e.g. Product Manager, Data Analyst'),
        F("search_location", "Search location", "str"),
        F("switch_number", "Switch search after N applications", "int"),
        F("randomize_search_order", "Randomize search order", "bool"),
        F("sort_by", "Sort by", "choice", ["", "Most recent", "Most relevant"]),
        F("date_posted", "Date posted", "choice",
          ["Past week", "Any time", "Past month", "Past 24 hours", ""]),
        F("salary", "Minimum salary", "choice",
          ["", "$40,000+", "$60,000+", "$80,000+", "$100,000+", "$120,000+",
           "$140,000+", "$160,000+", "$180,000+", "$200,000+"]),
        F("easy_apply_only", "Easy Apply only", "bool"),
        F("experience_level", "Experience level", "multichoice",
          ["Internship", "Entry level", "Associate", "Mid-Senior level",
           "Director", "Executive"]),
        F("job_type", "Job type", "multichoice",
          ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer",
           "Internship", "Other"]),
        F("on_site", "Workplace", "multichoice", ["On-site", "Remote", "Hybrid"]),
        F("companies", "Target companies (comma separated)", "list"),
        F("location", "Locations filter (comma separated)", "list"),
        F("industry", "Industry (comma separated)", "list"),
        F("job_function", "Job function (comma separated)", "list"),
        F("job_titles", "Job titles filter (comma separated)", "list"),
        F("under_10_applicants", "Under 10 applicants", "bool"),
        F("in_your_network", "In your network", "bool"),
        F("fair_chance_employer", "Fair chance employer", "bool"),
        F("pause_after_filters", "Pause after applying filters", "bool"),
        F("about_company_bad_words", "Skip companies w/ words", "list"),
        F("about_company_good_words", "Exception companies", "list"),
        F("bad_words", "Skip jobs w/ words in description", "list"),
        F("security_clearance", "Have security clearance", "bool"),
        F("did_masters", "Have a Master's degree", "bool"),
        F("current_experience", "Your experience (years, -1 = any)", "int"),
    ]),

    ("Account / AI", "secrets", [
        F("username", "LinkedIn email", "str",
          help="Leave default to log in manually each run"),
        F("password", "LinkedIn password", "str"),
        F("use_AI", "Use AI features", "bool"),
        F("ai_provider", "AI provider", "choice", ["claude", "openai", "deepseek", "gemini", "grok", "anthropic", "xai"]),
        F("llm_api_url", "LLM API URL", "str"),
        F("llm_api_key", "LLM API key", "str"),
        F("llm_model", "LLM model", "str"),
        F("llm_spec", "LLM spec", "choice",
          ["openai", "openai-like", "openai-like-github", "openai-like-mistral"]),
        F("stream_output", "Stream AI output", "bool"),
    ]),

    ("Bot Settings", "settings", [
        F("close_tabs", "Close external app tabs", "bool"),
        F("follow_companies", "Follow companies on apply", "bool"),
        F("run_non_stop", "Run non-stop", "bool"),
        F("alternate_sortby", "Alternate sort-by", "bool"),
        F("cycle_date_posted", "Cycle date-posted", "bool"),
        F("stop_date_cycle_at_24hr", "Stop date cycle at 24hr", "bool"),
        F("click_gap", "Max gap between clicks (s)", "int"),
        F("run_in_background", "Run Chrome in background", "bool"),
        F("disable_extensions", "Disable extensions", "bool"),
        F("safe_mode", "Safe mode (guest profile)", "bool"),
        F("smooth_scroll", "Smooth scrolling", "bool"),
        F("keep_screen_awake", "Keep screen awake", "bool"),
        F("stealth_mode", "Stealth mode (undetected)", "bool"),
        F("showAiErrorAlerts", "Show AI error alerts", "bool"),
        F("generated_resume_path", "Generated resumes folder", "str"),
        F("file_name", "Applied history CSV", "str"),
        F("failed_file_name", "Failed history CSV", "str"),
        F("logs_folder_path", "Logs folder", "str"),
    ]),
]


# --------------------------------------------------------------------------- #
# Scrollable frame
# --------------------------------------------------------------------------- #
class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._win, width=e.width),
        )
        # Mouse wheel only while the cursor is over this canvas
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_wheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _bind_wheel(self, _):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")


# --------------------------------------------------------------------------- #
# Main application
# --------------------------------------------------------------------------- #
class ConfigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinkedIn Auto Job Applier - Configuration")
        self.geometry("820x760")
        self.minsize(680, 560)

        self.fields = {}      # (file_key, var) -> {schema, get, set}
        self.proc = None
        self.out_queue = queue.Queue()

        self._build_header()
        self._build_tabs()
        self._build_actions()
        self._build_log()

        self.load_all()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._drain_output)

    # ----- UI construction ----- #
    def _build_header(self):
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="Fill in your profile & CV, then Save or Save & Run.",
                  font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Button(bar, text="Reload from files", command=self.load_all).pack(side="right")

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=4)

        for tab_title, file_key, fields in SCHEMA:
            sf = ScrollFrame(self.nb)
            self.nb.add(sf, text=tab_title)
            grid = ttk.Frame(sf.inner, padding=10)
            grid.pack(fill="both", expand=True)
            grid.columnconfigure(1, weight=1)

            row = 0
            for f in fields:
                row = self._build_field(grid, file_key, f, row)

    def _build_field(self, parent, file_key, f, row):
        label = ttk.Label(parent, text=f["label"], wraplength=240)
        label.grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=4)

        vtype = f["type"]
        getter = setter = None

        if vtype == "bool":
            var = tk.BooleanVar()
            ttk.Checkbutton(parent, variable=var).grid(row=row, column=1, sticky="w", pady=4)
            getter, setter = var.get, var.set

        elif vtype == "choice":
            var = tk.StringVar()
            cb = ttk.Combobox(parent, textvariable=var, values=f["options"], state="readonly")
            cb.grid(row=row, column=1, sticky="ew", pady=4)
            getter, setter = var.get, var.set

        elif vtype == "text":
            txt = tk.Text(parent, height=5, wrap="word")
            txt.grid(row=row, column=1, sticky="ew", pady=4)
            getter = lambda t=txt: t.get("1.0", "end").strip("\n")
            setter = lambda v, t=txt: (t.delete("1.0", "end"), t.insert("1.0", str(v).strip("\n")))

        elif vtype == "multichoice":
            holder = ttk.Frame(parent)
            holder.grid(row=row, column=1, sticky="ew", pady=4)
            cvars = {}
            for opt in f["options"]:
                bv = tk.BooleanVar()
                cvars[opt] = bv
                ttk.Checkbutton(holder, text=opt, variable=bv).pack(side="left", padx=(0, 8))
            getter = lambda cv=cvars: [o for o, b in cv.items() if b.get()]

            def setter(values, cv=cvars):
                values = values or []
                for o, b in cv.items():
                    b.set(o in values)

        else:  # str, int, list
            var = tk.StringVar()
            entry_row = ttk.Frame(parent)
            entry_row.grid(row=row, column=1, sticky="ew", pady=4)
            entry_row.columnconfigure(0, weight=1)
            show = "*" if f["var"] == "password" else ""
            entry = ttk.Entry(entry_row, textvariable=var, show=show)
            entry.grid(row=row, column=0, sticky="ew")

            if f["var"] == "password":
                def _toggle(e=entry, btn=None):
                    e.config(show="" if e.cget("show") else "*")
                ttk.Button(entry_row, text="show", width=6, command=_toggle).grid(row=0, column=1, padx=(4, 0))
            elif f["var"] == "default_resume_path":
                ttk.Button(entry_row, text="Browse", width=8,
                           command=lambda v=var: self._browse_resume(v)).grid(row=0, column=1, padx=(4, 0))

            getter, setter = var.get, var.set

        if f["help"]:
            ttk.Label(parent, text=f["help"], foreground="#666",
                      font=("TkDefaultFont", 8), wraplength=520).grid(
                row=row + 1, column=1, sticky="w")
            row += 1

        self.fields[(file_key, f["var"])] = {"schema": f, "get": getter, "set": setter}
        return row + 1

    def _build_actions(self):
        bar = ttk.Frame(self, padding=(10, 6))
        bar.pack(fill="x")
        self.status = ttk.Label(bar, text="Ready.", foreground="#444")
        self.status.pack(side="left")

        self.run_btn = ttk.Button(bar, text="2. Save & Run Bot", command=self.save_and_run)
        self.run_btn.pack(side="right", padx=4)
        self.stop_btn = ttk.Button(bar, text="Stop Bot", command=self.stop_bot, state="disabled")
        self.stop_btn.pack(side="right", padx=4)
        self.login_btn = ttk.Button(bar, text="1. Login to LinkedIn", command=self.login_linkedin)
        self.login_btn.pack(side="right", padx=4)
        ttk.Button(bar, text="Save All", command=self.save_all).pack(side="right", padx=4)

    def _build_log(self):
        frame = ttk.LabelFrame(self, text="Bot output", padding=4)
        frame.pack(fill="both", expand=False, padx=8, pady=(0, 8))
        self.log = tk.Text(frame, height=8, wrap="word", state="disabled",
                           background="#111", foreground="#ddd")
        sb = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

    # ----- helpers ----- #
    def _browse_resume(self, var):
        path = filedialog.askopenfilename(
            title="Select your resume",
            filetypes=[("PDF / Documents", "*.pdf *.doc *.docx"), ("All files", "*.*")])
        if path:
            var.set(path)

    def _log_write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    # ----- load / save ----- #
    def load_all(self):
        for file_key, path in FILES.items():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except FileNotFoundError:
                continue
            for (fk, var), entry in self.fields.items():
                if fk != file_key:
                    continue
                f = entry["schema"]
                value = read_value(content, var, f["multiline"])
                if value is None and f["type"] not in ("list", "multichoice"):
                    continue
                self._apply_to_widget(entry, value)
        self.status.config(text="Loaded current values from config files.")

    def _apply_to_widget(self, entry, value):
        vtype = entry["schema"]["type"]
        if vtype == "bool":
            entry["set"](bool(value))
        elif vtype in ("list", "multichoice"):
            items = value if isinstance(value, list) else ([] if value in (None, "") else [value])
            if vtype == "list":
                entry["set"](", ".join(str(x) for x in items))
            else:
                entry["set"](items)
        elif vtype == "int":
            entry["set"]("" if value is None else str(value))
        else:
            entry["set"]("" if value is None else str(value))

    def save_all(self):
        try:
            for file_key, path in FILES.items():
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                for (fk, var), entry in self.fields.items():
                    if fk != file_key:
                        continue
                    f = entry["schema"]
                    literal = to_literal(entry["get"](), f["type"])
                    content = set_value(content, var, literal, f["multiline"])
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return False
        self.status.config(text="Saved all settings to /config.")
        return True

    # ----- run / stop ----- #
    def _launch(self, script, started_msg, status_msg):
        '''Launches a python script in a subprocess and streams its output.'''
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("Already running", "Something is already running. Stop it first.")
            return False
        try:
            self.proc = subprocess.Popen(
                [sys.executable, "-u", os.path.join(HERE, script)],
                cwd=HERE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            messagebox.showerror("Could not start", str(exc))
            return False
        self.run_btn.config(state="disabled")
        self.login_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text=status_msg)
        self._log_write(f"\n=== {started_msg} ===\n")
        threading.Thread(target=self._reader_thread, args=(self.proc,), daemon=True).start()
        return True

    def login_linkedin(self):
        if not self.save_all():
            return
        if not messagebox.askyesno(
                "Manual LinkedIn login",
                "Chrome will open on the LinkedIn login page.\n\n"
                "Log in by hand (including any 2FA/captcha), then click "
                "\"OK, I'm logged in\" in the small dialog.\n\n"
                "Your session is saved, so the bot will already be logged in afterwards.\n\nOpen it now?"):
            return
        self._launch("manual_login.py", "Manual login started", "Waiting for you to log in...")

    def save_and_run(self):
        if not self.save_all():
            return
        if not messagebox.askyesno(
                "Run bot",
                "Launch runAiBot.py now?\n\nA Chrome window will open and start "
                "applying. Keep an eye on it."):
            return
        self._launch("runAiBot.py", "Bot started", "Bot running...")

    def _reader_thread(self, proc):
        for line in iter(proc.stdout.readline, ""):
            self.out_queue.put(line)
        proc.stdout.close()
        rc = proc.wait()
        self.out_queue.put(f"\n=== Bot stopped (exit code {rc}) ===\n")
        self.out_queue.put(("__DONE__", rc))

    def _drain_output(self):
        try:
            while True:
                item = self.out_queue.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "__DONE__":
                    self.run_btn.config(state="normal")
                    self.login_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.status.config(text="Bot finished.")
                else:
                    self._log_write(item)
        except queue.Empty:
            pass
        self.after(120, self._drain_output)

    def stop_bot(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.config(text="Stopping bot...")

    def _on_close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Quit", "The bot is still running. Stop it and quit?"):
                return
            self.proc.terminate()
        self.destroy()


def main():
    app = ConfigApp()
    app.mainloop()


if __name__ == "__main__":
    main()
