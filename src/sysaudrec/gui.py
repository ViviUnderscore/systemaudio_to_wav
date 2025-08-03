# -*- coding: utf-8 -*-
"""Tkinter GUI for sysaudrec - folder dialog (helper process in dev, PowerShell in EXE) and logging."""

import os
import sys
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from sysaudrec.paths import default_recordings_dir
from sysaudrec.recorder import SystemAudioRecorder


# -------------------- logging --------------------
def _ensure_logs_dir() -> str:
    path = os.path.abspath(os.path.join(os.getcwd(), "logs"))
    os.makedirs(path, exist_ok=True)
    return path

def _setup_logging() -> str:
    log_dir = _ensure_logs_dir()
    log_path = os.path.join(log_dir, "sysaudrec.log")
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        root.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        ch.setLevel(logging.INFO)
        root.addHandler(ch)

    logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    return log_path

_LOG_PATH = _setup_logging()
log = logging.getLogger(__name__)
# -------------------------------------------------


# -------------------- folder picker (works in dev and in packaged EXE) --------------------
IS_FROZEN = bool(getattr(sys, "frozen", False))

def _pick_folder_external(initial_dir: str) -> Optional[str]:
    """
    Open a folder picker in a short-lived helper process to avoid Tk hangs.
      - Dev (not frozen): launch a tiny Python -c that uses Tk's askdirectory.
      - Frozen (EXE): use PowerShell's FolderBrowserDialog (Explorer UI).
    Return normalized path or None.
    """
    init = initial_dir.replace('\\', '\\\\')

    if not IS_FROZEN:
        # Use current interpreter so venv works
        helper = (
            "import tkinter as tk;"
            "from tkinter import filedialog;"
            "r=tk.Tk(); r.withdraw(); r.update_idletasks();"
            f"p=filedialog.askdirectory(title='Select Output Folder', initialdir=r'{init}');"
            "print(p if p else '');"
            "r.destroy();"
        )
        try:
            proc = subprocess.run([sys.executable, "-c", helper],
                                  capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                out = (proc.stdout or "").strip()
                return os.path.normpath(out) if out else None
            log.error("folder helper rc=%s stderr=%s", proc.returncode, (proc.stderr or "").strip())
        except Exception as e:
            log.exception("folder helper failed: %s", e)
        return None

    # Frozen: use Explorer dialog via PowerShell (single-threaded apartment)
    ps = (
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
        f"$p = '{init}'; "
        "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$f.Description = 'Select Output Folder'; $f.SelectedPath = $p; "
        "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Write-Output $f.SelectedPath }"
    )
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                              capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            out = (proc.stdout or "").strip()
            return os.path.normpath(out) if out else None
        log.error("powershell helper rc=%s stderr=%s", proc.returncode, (proc.stderr or "").strip())
    except Exception as e:
        log.exception("powershell helper failed: %s", e)
    return None
# ------------------------------------------------------------------------------------------


class RecorderWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("System Audio Recorder (WAV)")
        self.geometry("600x300")

        self.recorder = SystemAudioRecorder()
        self.output_folder = tk.StringVar(value=default_recordings_dir())
        self.filename = tk.StringVar(value="")  # optional name without extension
        self.status = tk.StringVar(value="Idle")

        self._build_ui()
        self._update_buttons()
        log.info("GUI initialized. output_folder=%s log=%s (frozen=%s)", self.output_folder.get(), _LOG_PATH, IS_FROZEN)

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 8}

        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        # Output folder row
        row1 = ttk.Frame(root)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="Output folder:").pack(side="left")
        self.entry_folder = ttk.Entry(row1, textvariable=self.output_folder)
        self.entry_folder.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.btn_browse = ttk.Button(row1, text="Browse...", command=self.choose_folder)
        self.btn_browse.pack(side="left")

        # Optional file name row
        row1b = ttk.Frame(root)
        row1b.pack(fill="x", **pad)
        ttk.Label(row1b, text="File name (optional):").pack(side="left")
        self.entry_name = ttk.Entry(row1b, textvariable=self.filename)
        self.entry_name.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Label(row1b, text=".wav").pack(side="left")

        # Buttons
        row2 = ttk.Frame(root)
        row2.pack(fill="x", **pad)
        self.btn_record = ttk.Button(row2, text="Record", command=self.start_recording)
        self.btn_record.pack(side="left")
        self.btn_stop = ttk.Button(row2, text="Stop", command=self.stop_recording)
        self.btn_stop.pack(side="left", padx=(8, 0))

        # Status
        row3 = ttk.Frame(root)
        row3.pack(fill="x", **pad)
        ttk.Label(row3, text="Status:").pack(side="left")
        ttk.Label(row3, textvariable=self.status).pack(side="left", padx=(8, 0))

        note = ttk.Label(
            root,
            text="Leave file name blank to use a timestamped name. Existing names get _01, _02, etc.",
            wraplength=560,
            foreground="#444",
        )
        note.pack(fill="x", **pad)

    def _update_buttons(self, recording: Optional[bool] = None) -> None:
        if recording is None:
            recording = (self.status.get() == "Recording")
        self.btn_record.config(state=("disabled" if recording else "normal"))
        self.btn_stop.config(state=("normal" if recording else "disabled"))
        self.btn_browse.config(state=("disabled" if recording else "normal"))

    def _safe_initial_dir(self) -> str:
        init = self.output_folder.get().strip()
        if init and os.path.isdir(init):
            return os.path.normpath(init)
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.isdir(docs):
            return os.path.normpath(docs)
        home = os.path.expanduser("~")
        if os.path.isdir(home):
            return os.path.normpath(home)
        return "C:\\"

    def choose_folder(self) -> None:
        self.btn_browse.config(state="disabled")
        self.update_idletasks()
        try:
            initdir = self._safe_initial_dir()
            log.info("Browse clicked. mode=%s init=%s", "frozen" if IS_FROZEN else "dev", initdir)
            folder = _pick_folder_external(initdir)
            if folder:
                self.output_folder.set(folder)
                log.info("Browse selected: %s", folder)
            else:
                log.info("Browse canceled or no selection.")
        except Exception as e:
            log.exception("Browse failed: %s", e)
            messagebox.showerror("Error", f"Browse failed:\n{e}")
        finally:
            self.btn_browse.config(state="normal")

    def start_recording(self) -> None:
        folder = self.output_folder.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please choose an output folder.")
            return
        try:
            name = self.filename.get().strip() or None
            path = self.recorder.start(folder, filename=name)
            self.status.set("Recording")
            self._update_buttons(recording=True)
            log.info("Start recording -> %s", path)
            print("Recording to:", path)
        except Exception as e:
            log.exception("Error starting recording: %s", e)
            messagebox.showerror("Error starting recording", str(e))
            self.status.set("Idle")
            self._update_buttons(recording=False)

    def stop_recording(self) -> None:
        try:
            path = self.recorder.stop()
            self.status.set("Idle")
            self._update_buttons(recording=False)
            log.info("Stop recording -> %s", path)
            if path and os.path.exists(path):
                messagebox.showinfo("Saved", f"Saved: {path}")
        except Exception as e:
            log.exception("Error stopping recording: %s", e)
            messagebox.showerror("Error stopping recording", str(e))
