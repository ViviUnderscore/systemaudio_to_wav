# -*- coding: utf-8 -*-
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def resource_path(relative: str) -> str:
    """
    Resolve a resource path that works for both dev and PyInstaller onefile.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = getattr(sys, "_MEIPASS")  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def default_recordings_dir() -> str:
    """
    Default output folder. Uses ./recordings under the current working directory.
    """
    path = os.path.abspath(os.path.join(os.getcwd(), "recordings"))
    os.makedirs(path, exist_ok=True)
    return path


def logs_dir() -> str:
    """
    Log directory under the current working directory: ./logs
    """
    path = os.path.abspath(os.path.join(os.getcwd(), "logs"))
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging(app_name: str = "sysaudrec", level: int = logging.INFO) -> str:
    """
    Configure logging with a rotating file handler and a simple console handler.
    Returns the log file path.
    """
    log_path = os.path.join(logs_dir(), f"{app_name}.log")

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers (avoid duplicates on reload)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_h = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_h.setFormatter(fmt)
    file_h.setLevel(level)
    root.addHandler(file_h)

    console_h = logging.StreamHandler()
    console_h.setFormatter(fmt)
    console_h.setLevel(level)
    root.addHandler(console_h)

    logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    return log_path
