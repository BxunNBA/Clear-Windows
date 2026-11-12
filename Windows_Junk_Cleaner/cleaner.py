"""
Windows Junk & Temporary Files Cleaner
======================================
A Python script to safely clean up temporary and junk files on Windows.
Features include dry-run mode, admin privilege handling, and Unicode support.
"""

import os
import re
import sys
import shutil
import ctypes
import argparse
import textwrap
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ──────────────────────────────────────────────────────────────────────────────
#  Styling helpers
# ──────────────────────────────────────────────────────────────────────────────
ESC = "\033"


class Colors:
    RESET = f"{ESC}[0m"
    BOLD = f"{ESC}[1m"
    DIM = f"{ESC}[2m"
    GRAY = f"{ESC}[90m"
    RED = f"{ESC}[91m"
    GREEN = f"{ESC}[92m"
    YELLOW = f"{ESC}[93m"
    BLUE = f"{ESC}[94m"
    MAGENTA = f"{ESC}[95m"
    CYAN = f"{ESC}[96m"


C = Colors
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

LOGO_ART = r"""
     ██████╗██╗     ███████╗ █████╗ ██████╗ ██╗██╗
    ██╔════╝██║     ██╔════╝██╔══██╗██╔══██╗██║██║
    ██║     ██║     █████╗  ███████║██████╔╝██║██║
    ██║     ██║     ██╔══╝  ██╔══██║██╔══██╗╚═╝╚═╝
    ╚██████╗███████╗███████╗██║  ██║██║  ██║██╗██╗
     ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝
"""
CREDIT = "MAKE BY : DLS.BXUN"
GRADIENT = [51, 45, 39, 33, 27, 63]  # 256-colour cyan -> blue/violet

# Layout (set once at start-up by setup_layout)
WIDTH = 78
MARGIN = 0


def vlen(text: str) -> int:
    """Visible length of a string (ANSI escape codes are ignored)."""
    return len(ANSI_RE.sub("", text))


WINDOW_COLS = 100
WINDOW_LINES = 48


def fit_window() -> None:
    """Resize the console so the whole start-up screen is visible, then clear it.

    Needed because the elevated (Administrator) window is a brand-new console
    that does not inherit the size set by run_cleaner.cmd.
    """
    if sys.platform != "win32":
        return
    try:
        os.system(f"mode con: cols={WINDOW_COLS} lines={WINDOW_LINES}")
        os.system("cls")
    except Exception:
        pass


def setup_layout() -> None:
    """Pick a content width that fits the terminal, and centre it."""
    global WIDTH, MARGIN
    cols = shutil.get_terminal_size((100, 30)).columns
    WIDTH = max(56, min(cols - 2, 80))
    MARGIN = max((cols - WIDTH) // 2, 0)


def emit(text: str = "") -> None:
    print(" " * MARGIN + text)


def center(text: str) -> None:
    emit(" " * max((WIDTH - vlen(text)) // 2, 0) + text)


def rule(char: str = "─", color: str = C.GRAY) -> None:
    emit(f"{color}{char * WIDTH}{C.RESET}")


def section(title: str) -> None:
    head = f"── {title} "
    emit(f"{C.CYAN}{head}{'─' * max(WIDTH - len(head), 0)}{C.RESET}")


def box(lines: List[str], color: str = C.CYAN) -> None:
    inner = WIDTH - 2
    emit(f"{color}╔{'═' * inner}╗{C.RESET}")
    for ln in lines:
        emit(f"{color}║{C.RESET}{ln}{' ' * max(inner - vlen(ln), 0)}{color}║{C.RESET}")
    emit(f"{color}╚{'═' * inner}╝{C.RESET}")


def truncate_middle(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    keep = max(width - 3, 2)
    head = keep // 2 + keep % 2
    return text[:head] + "..." + text[-(keep - head):]


def kv(label: str, value: str) -> None:
    emit(f"  {C.GRAY}{label:<11}{C.RESET}{value}")


def print_logo() -> None:
    """Print the logo as ONE block, centred as a whole (keeps the art aligned)."""
    lines = textwrap.dedent(LOGO_ART).strip("\n").split("\n")
    block_w = max(len(l) for l in lines)
    pad = " " * max((WIDTH - block_w) // 2, 0)
    for i, line in enumerate(lines):
        color = f"{ESC}[38;5;{GRADIENT[i % len(GRADIENT)]}m"
        emit(f"{pad}{color}{line.ljust(block_w)}{C.RESET}")
    emit()
    center(f"{C.BOLD}{C.CYAN}{CREDIT}{C.RESET}")
    center(f"{C.GRAY}Windows Junk & Temporary Files Cleaner{C.RESET}")
    rule("═")


# ──────────────────────────────────────────────────────────────────────────────
#  Core logic
# ──────────────────────────────────────────────────────────────────────────────
def is_admin() -> bool:
    """Check if the script is running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def format_size(bytes_size: float) -> str:
    """Convert a size in bytes to a human-readable string (B, KB, MB, ...)."""
    if bytes_size < 1024:
        return f"{int(bytes_size)} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        bytes_size /= 1024
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
    return f"{bytes_size / 1024:.2f} PB"


def get_target_directories() -> List[Dict[str, Any]]:
    """Return a list of directories that the cleaner will process."""
    user_home = Path.home()
    local_appdata = Path(os.getenv("LOCALAPPDATA", user_home / "AppData" / "Local"))
    appdata = Path(os.getenv("APPDATA", user_home / "AppData" / "Roaming"))
    windir = Path(os.getenv("WINDIR", "C:\\Windows"))
    progdata = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData"))

    def t(category, description, path, admin):
        return {
            "category": category,
            "description": description,
            "path": path,
            "clean_mode": "contents",
            "requires_admin": admin,
        }

    return [
        t("User Temp Files", "Temporary files stored in the user profile.",
          local_appdata / "Temp", False),
        t("Windows System Temp", "System-level temporary files.",
          windir / "Temp", True),
        t("Windows Prefetch", "Prefetch cache used to speed up application launch.",
          windir / "Prefetch", True),
        t("Windows Update Cache", "Downloaded Windows Update packages.",
          windir / "SoftwareDistribution" / "Download", True),
        t("Windows Delivery Optimization", "Distributed download cache for Windows Update.",
          windir / "SoftwareDistribution" / "DeliveryOptimization", True),
        t("Crash Dumps & Error Reports", "Local crash dump files and error reports.",
          local_appdata / "CrashDumps", False),
        t("Windows Error Reporting (WER)", "WER report queue.",
          progdata / "Microsoft" / "Windows" / "WER" / "ReportQueue", True),
        t("Google Chrome Cache", "Cache of web pages and images for Chrome.",
          local_appdata / "Google" / "Chrome" / "User Data" / "Default" / "Cache", False),
        t("Google Chrome Code Cache", "JS/Wasm code cache for Chrome.",
          local_appdata / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache", False),
        t("Microsoft Edge Cache", "Cache of web pages and images for Edge.",
          local_appdata / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache", False),
        t("Microsoft Edge Code Cache", "Code cache for Edge.",
          local_appdata / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache", False),
        t("Python pip Cache", "Cached Python packages downloaded by pip.",
          local_appdata / "pip" / "cache", False),
        t("Node.js npm Cache", "Cached npm packages.",
          appdata / "npm-cache", False),
        t("Windows CBS Logs", "Component-Based Servicing logs.",
          windir / "Logs" / "CBS", True),
    ]


def scan_directory(target_path: Path) -> Tuple[int, int]:
    """Count files and total size within a directory."""
    total_files = 0
    total_size = 0
    if not target_path.exists():
        return 0, 0
    try:
        for entry in target_path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total_files += 1
                    total_size += entry.stat().st_size
            except (PermissionError, FileNotFoundError, OSError):
                continue
    except Exception:
        pass
    return total_files, total_size


def clean_target(target_path: Path, dry_run: bool = False) -> Tuple[int, int, int]:
    """Delete files and subfolders in *target_path*.
    Returns (deleted_files, freed_bytes, skipped_errors).
    """
    deleted_files = 0
    freed_bytes = 0
    skipped_errors = 0
    if not target_path.exists():
        return 0, 0, 0
    try:
        items = list(target_path.iterdir())
    except (PermissionError, OSError):
        return 0, 0, 1
    for item in items:
        try:
            if item.is_file() or item.is_symlink():
                size = 0
                try:
                    size = item.stat().st_size
                except Exception:
                    pass
                if not dry_run:
                    item.unlink(missing_ok=True)
                deleted_files += 1
                freed_bytes += size
            elif item.is_dir():
                dir_files, dir_size = scan_directory(item)
                if not dry_run:
                    shutil.rmtree(item, ignore_errors=True)
                deleted_files += dir_files
                freed_bytes += dir_size
        except (PermissionError, OSError):
            skipped_errors += 1
            continue
    return deleted_files, freed_bytes, skipped_errors


def empty_recycle_bin(dry_run: bool = False) -> bool:
    """Empty the Windows Recycle Bin."""
    if dry_run:
        return True
    try:
        # SHEmptyRecycleBinW flags: 0x7 (no UI, no progress, no sound)
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        return result in (0, -2147418113, 0x8000FFFF, -2147024894, 0x80070002)
    except Exception:
        return False


def enable_console_features() -> None:
    """Turn on ANSI colours and UTF-8 output on Windows."""
    if sys.platform == "win32":
        try:
            k32 = ctypes.windll.kernel32
            for std_handle in (-11, -12):  # stdout, stderr
                h = k32.GetStdHandle(std_handle)
                mode = ctypes.c_ulong()
                if k32.GetConsoleMode(h, ctypes.byref(mode)):
                    k32.SetConsoleMode(h, mode.value | 0x0004)  # VIRTUAL_TERMINAL
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  Output rows
# ──────────────────────────────────────────────────────────────────────────────
NAME_W = 30
FILES_W = 8
SIZE_W = 12


def result_header() -> None:
    emit(f"  {C.GRAY}{'':3} {'CATEGORY':<{NAME_W}}{'FILES':>{FILES_W}}{'FREED':>{SIZE_W}}  NOTE{C.RESET}")
    emit(f"  {C.GRAY}{'─' * (WIDTH - 4)}{C.RESET}")


def result_row(marker: str, color: str, name: str, files: str, size: str, note: str = "") -> None:
    note_w = max(WIDTH - (2 + 3 + 1 + NAME_W + FILES_W + SIZE_W + 2), 0)
    note = note[:note_w]
    emit(f"  {color}{marker}{C.RESET} {name:<{NAME_W}}{files:>{FILES_W}}{size:>{SIZE_W}}  {C.GRAY}{note}{C.RESET}")


def dotted(label: str, value: str, inner: int) -> str:
    dots = max(inner - 4 - len(label) - vlen(value), 2)
    return f" {label} {C.DIM}{'.' * dots}{C.RESET} {value} "


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Windows Junk & Temporary Files Cleaner")
    parser.add_argument("--dry-run", action="store_true", help="Simulate cleanup without deleting files")
    parser.add_argument("--force", "-y", action="store_true", help="Skip confirmation prompts and delete immediately")
    parser.add_argument("--skip-recycle-bin", action="store_true", help="Do not empty the Recycle Bin")
    args = parser.parse_args()

    enable_console_features()
    fit_window()
    setup_layout()
    print_logo()

    admin_status = is_admin()
    if admin_status:
        priv = f"{C.GREEN}[OK] Administrator (full system access){C.RESET}"
    else:
        priv = f"{C.YELLOW}[!] Standard user (run as admin for full cleaning){C.RESET}"
    mode = (f"{C.YELLOW}DRY-RUN (simulation only){C.RESET}" if args.dry_run
            else f"{C.RED}LIVE DELETION{C.RESET}")

    emit()
    kv("Privilege", priv)
    kv("Mode", mode)

    targets = get_target_directories()
    kv("Targets", f"{len(targets)} locations" + ("" if args.skip_recycle_bin else " + Recycle Bin"))
    emit()

    # ── Target list ──────────────────────────────────────────────────────────
    section("Target locations")
    for i, tg in enumerate(targets, 1):
        exists = tg["path"].exists()
        tag = f"{C.GREEN}EXISTS {C.RESET}" if exists else f"{C.RED}MISSING{C.RESET}"
        left = f"  {C.GRAY}{i:>2}{C.RESET}  {tag}  {C.BOLD}{tg['category']}{C.RESET}"
        right = ""
        if tg["requires_admin"]:
            right = f"{C.YELLOW}ADMIN{C.RESET}" if not admin_status else f"{C.GRAY}admin{C.RESET}"
        gap = max(WIDTH - vlen(left) - vlen(right) - 2, 1)
        emit(left + " " * gap + right)
        emit(f"      {C.DIM}{truncate_middle(str(tg['path']), WIDTH - 8)}{C.RESET}")
    rule()

    # ── Confirmation ─────────────────────────────────────────────────────────
    if not args.dry_run and not args.force:
        try:
            confirm = input(" " * MARGIN + f"  {C.BOLD}Proceed with cleanup? [y/N]: {C.RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            emit(f"\n  {C.YELLOW}Operation cancelled by user.{C.RESET}\n")
            sys.exit(0)
        if confirm not in ("y", "yes"):
            emit(f"  {C.YELLOW}Operation cancelled by user.{C.RESET}\n")
            sys.exit(0)

    emit()
    section("Cleaning in progress" if not args.dry_run else "Simulating cleanup")
    emit()
    result_header()

    grand_files = 0
    grand_size = 0
    grand_skipped = 0

    for tg in targets:
        name = tg["category"]
        path = tg["path"]
        if not path.exists():
            result_row("[-]", C.GRAY, name, "-", "-", "not found")
            continue
        if tg["requires_admin"] and not admin_status:
            result_row("[-]", C.YELLOW, name, "-", "-", "needs admin")
            continue
        deleted, freed, skipped = clean_target(path, dry_run=args.dry_run)
        grand_files += deleted
        grand_size += freed
        grand_skipped += skipped
        note = f"{skipped} locked" if skipped else ""
        result_row("[+]" if not skipped else "[!]", C.GREEN if not skipped else C.YELLOW,
                   name, f"{deleted:,}", format_size(freed), note)

    if not args.skip_recycle_bin:
        if args.dry_run:
            result_row("[+]", C.GREEN, "Windows Recycle Bin", "-", "-", "dry-run")
        elif empty_recycle_bin(dry_run=False):
            result_row("[+]", C.GREEN, "Windows Recycle Bin", "-", "-", "emptied")
        else:
            result_row("[-]", C.YELLOW, "Windows Recycle Bin", "-", "-", "empty / failed")

    # ── Summary ──────────────────────────────────────────────────────────────
    emit()
    inner = WIDTH - 2
    title = "SUMMARY - DRY RUN" if args.dry_run else "SUMMARY - COMPLETED"
    title_ln = " " * ((inner - len(title)) // 2) + f"{C.BOLD}{C.GREEN}{title}{C.RESET}"
    lines = [
        title_ln,
        " " * inner,
        dotted("Files processed", f"{grand_files:,}", inner),
        dotted("Space reclaimed" if not args.dry_run else "Space reclaimable",
               f"{C.BOLD}{C.GREEN}{format_size(grand_size)}{C.RESET}", inner),
    ]
    if grand_skipped:
        lines.append(dotted("Files skipped", f"{C.YELLOW}{grand_skipped:,}{C.RESET}", inner))
    box(lines, C.GREEN)
    emit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Interrupted by user.{C.RESET}")
        sys.exit(0)
