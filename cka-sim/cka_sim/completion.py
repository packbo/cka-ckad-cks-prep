"""Tab-completion + history for the scenario prompt.

- kubectl completion delegated to `kubectl __complete` (same engine as the official
  bash completion) → completes subcommands, flags, resources, even pod names.
- Exam aliases (k, kgp, kgs...) expanded for BOTH completion and execution.
- $do / $now shortcuts expanded (see CKA/setup-environnement.md).
- Persistent command history (up-arrow across sessions).
"""
from __future__ import annotations

import atexit
import glob
import os
import shlex
import subprocess

try:
    import readline
    HAVE_READLINE = True
except ImportError:  # windows / odd builds
    HAVE_READLINE = False

ALIASES = {
    "k": "kubectl",
    "kgp": "kubectl get pods",
    "kgd": "kubectl get deployments",
    "kgs": "kubectl get svc",
    "kgn": "kubectl get nodes",
    "kgns": "kubectl get namespaces",
    "kd": "kubectl describe",
    "kdel": "kubectl delete",
    "kaf": "kubectl apply -f",
    "kex": "kubectl exec -it",
    "klog": "kubectl logs",
    "kcf": "kubectl config",
}

VAR_SHORTCUTS = {
    "$do": "--dry-run=client -o yaml",
    "$now": "--force --grace-period=0",
}

META_COMMANDS = [
    ":hint", ":check", ":cheat", ":cheatsheet", ":tag", ":untag",
    ":back", ":goto", ":solution", ":skip", ":next", ":quit", ":exit",
]
FIRST_WORDS = sorted(set(ALIASES) | {
    "kubectl", "kind", "helm", "jq", "grep", "cat", "curl", "echo", "vim", "clear",
})

HISTORY_FILE = os.path.expanduser("~/.cache/cka-sim/history")


def expand_command(raw: str) -> str:
    """Expand exam aliases ($do/$now + k/kgp/...) so commands actually run."""
    out = raw
    for var, val in VAR_SHORTCUTS.items():
        out = out.replace(var, val)
    parts = out.split(maxsplit=1)
    if parts and parts[0] in ALIASES:
        rest = parts[1] if len(parts) > 1 else ""
        out = f"{ALIASES[parts[0]]} {rest}"
    return out.strip()


def _tokens(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError:  # unbalanced quote while typing
        return line.split()


def _kubectl_complete(prior_words: list[str], to_complete: str) -> list[str]:
    try:
        cp = subprocess.run(
            ["kubectl", "__complete", *prior_words, to_complete],
            capture_output=True, text=True, timeout=3,
        )
    except Exception:
        return []
    out = []
    out = []
    for ln in cp.stdout.splitlines():
        if ln.startswith(":"):  # directive marker: candidates end here
            break
        if ln:
            out.append(ln.split("\t")[0])  # drop the description column
    return [c for c in out if c.startswith(to_complete)]


def candidates(line: str, text: str) -> list[str]:
    """Completion candidates for the given buffer + word being typed."""
    line = line.lstrip()

    if not line or (not _tokens(line) and not text):
        return [w for w in FIRST_WORDS if w.startswith(text)]

    if line.startswith(":"):
        if " " not in line:
            return [m for m in META_COMMANDS if m.startswith(text)]
        first = line.split()[0]
        if first == ":hint":
            return [n for n in ("1", "2", "3", "4") if n.startswith(text)]
        if first == ":goto":
            return [str(n) for n in range(1, 21) if str(n).startswith(text)]
        if first in (":cheat", ":cheatsheet"):
            from cka_sim import cheatsheet
            return [t for t in cheatsheet.topics() if t.startswith(text)]
        return []

    expanded = expand_command(line)
    exp_toks = expanded.split()
    if exp_toks and exp_toks[0] == "kubectl":
        # prior words (after 'kubectl'), word being typed = raw text
        if line.endswith(" "):
            prior = _tokens(expanded)[1:]
        else:
            prior = _tokens(expanded)[1:-1] if len(exp_toks) > 1 else []
        return _kubectl_complete(prior, text)

    if not _tokens(line) and text:  # typing the first word
        return [w for w in FIRST_WORDS if w.startswith(text)]

    # default: filename completion (vim foo<TAB>, cat ...)
    if text:
        pattern = glob.escape(text) + "*"
        return sorted(glob.glob(pattern))[:50]
    return []


_last_cache: tuple[str, str, list[str]] = ("", "", [])


def _completer(text: str, state: int):
    line = readline.get_line_buffer()
    key = (line, text)
    if _last_cache[:2] != key:
        globals()["_last_cache"] = (line, text, candidates(line, text))
    matches = _last_cache[2]
    return matches[state] if state < len(matches) else None


def setup() -> None:
    """Enable completion + persistent history for the current process."""
    if not HAVE_READLINE:
        return
    readline.set_completer(_completer)
    if "libedit" in (readline.__doc__ or ""):  # macOS
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
        readline.set_history_length(1000)
        atexit.register(_save_history)
    except OSError:
        pass


def _save_history() -> None:
    try:
        readline.write_history_file(HISTORY_FILE)
    except OSError:
        pass
