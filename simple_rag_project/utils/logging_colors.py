"""彩色日誌工具"""
import logging
import platform
import os
from pathlib import Path

DANGER_LEVEL = 45
logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def danger(self, message, *args, **kwargs):
    if self.isEnabledFor(DANGER_LEVEL):
        self._log(DANGER_LEVEL, message, args, **kwargs)

logging.addLevelName(DANGER_LEVEL, "DANGER")
logging.Logger.danger = danger


def add_coloring_to_emit_windows(fn):
    def _set_color(self, code):
        import ctypes
        STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        FOREGROUND_BLUE = 0x0001
        FOREGROUND_GREEN = 0x0002
        FOREGROUND_RED = 0x0004
        FOREGROUND_INTENSITY = 0x0008
        FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
        FOREGROUND_BLACK = 0x0000
        FOREGROUND_MAGENTA = 0x0005
        FOREGROUND_YELLOW = 0x0006
        BACKGROUND_BLACK = 0x0000
        BACKGROUND_YELLOW = 0x0060
        BACKGROUND_INTENSITY = 0x0080

        levelno = args[1].levelno
        if levelno >= 50:
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
        elif levelno >= 40:
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif levelno >= 30:
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif levelno >= 20:
            color = FOREGROUND_GREEN
        elif levelno >= 10:
            color = FOREGROUND_MAGENTA
        else:
            color = FOREGROUND_WHITE

        args[0]._set_color(color)
        res = fn(*args)
        args[0]._set_color(FOREGROUND_WHITE)
        return res

    return new


def add_coloring_to_emit_ansi(fn):
    def new(*args):
        levelno = args[1].levelno
        if levelno >= 50:
            color = '\x1b[31m'
        elif levelno >= 40:
            color = '\x1b[31m'
        elif levelno >= 30:
            color = '\x1b[33m'
        elif levelno >= 20:
            color = '\x1b[32m'
        elif levelno >= 10:
            color = '\x1b[35m'
        else:
            color = '\x1b[0m'

        args[1].msg = color + str(args[1].msg) + '\x1b[0m'
        return fn(*args)
    return new


# Apply color patch
if platform.system() == 'Windows':
    logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
else:
    logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)


ENABLE_LOG_TO_FILE = os.environ.get("ENABLE_LOG_TO_FILE", "0")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

# File handlers (if enabled)
if ENABLE_LOG_TO_FILE == "1":
    log_dir = Path("./log")
    log_dir.mkdir(exist_ok=True)

    log_files = {
        logging.DEBUG: log_dir / "debug.log",
        logging.INFO: log_dir / "info.log",
        logging.WARNING: log_dir / "warning.log",
        logging.ERROR: log_dir / "error.log",
        logging.CRITICAL: log_dir / "critical.log",
        DANGER_LEVEL: log_dir / "danger.log",
    }

    for level, filename in log_files.items():
        handler = logging.FileHandler(filename, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s:%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)
