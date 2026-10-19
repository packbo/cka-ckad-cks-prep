"""Shared paths, cert-aware (cka | ckad | cks)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS_ROOT = os.path.join(ROOT, "scenarios")
EXAMS_ROOT = os.path.join(ROOT, "exams")
DATA_DIR = os.path.join(ROOT, "data")
CHEATSHEET_PATH = os.path.join(DATA_DIR, "cheatsheet.json")

DEFAULT_CERT = os.environ.get("CKA_SIM_CERT", "cka")
CERTS = ("cka", "ckad", "cks")

_active_cert = DEFAULT_CERT


def set_cert(cert: str) -> None:
    global _active_cert
    _active_cert = (cert or DEFAULT_CERT).strip().lower() or DEFAULT_CERT


def active_cert() -> str:
    return _active_cert


def scenarios_dir(cert: str = None) -> str:
    return os.path.join(SCENARIOS_ROOT, cert or _active_cert)


def exams_dir(cert: str = None) -> str:
    return os.path.join(EXAMS_ROOT, cert or _active_cert)


# Back-compat aliases (older modules / imports)
SCENARIOS_DIR = SCENARIOS_ROOT
EXAMS_DIR = EXAMS_ROOT
