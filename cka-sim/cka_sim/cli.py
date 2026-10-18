"""CLI entry point: list / run / exam / up / down / reset / status."""
from __future__ import annotations

import argparse
import sys

import yaml

from cka_sim import ui
from cka_sim.cluster import KindBackend, kind_installed, kubectl_installed
from cka_sim.engine import ScenarioResult, load_scenarios, run_scenario
from cka_sim.paths import EXAMS_DIR
from cka_sim.reporter import report
from cka_sim.timer import Timer

backend = KindBackend()


def cmd_list(args):
    scen = load_scenarios()
    if not scen:
        ui.warn("no scenarios found in scenarios/")
        return
    print(f"{'id':28} {'domain':22} {'weight':>6} {'diff':8} title")
    print("-" * 90)
    for s in scen:
        print(f"{s.id:28} {s.domain:22} {s.weight:>6} {s.difficulty:8} {s.title}")


def _require_ready():
    if not backend.ready():
        ui.warn("cluster not ready. Run:  ./run.sh up")
        return False
    return True


def cmd_run(args):
    if not _require_ready():
        return
    scen = {s.id: s for s in load_scenarios()}
    if args.id not in scen:
        ui.warn(f"unknown scenario '{args.id}'. Available:")
        for k in scen:
            print("  " + k)
        return
    run_scenario(scen[args.id], backend)


def cmd_exam(args):
    if not _require_ready():
        return
    import os

    exam_path = os.path.join(EXAMS_DIR, args.exam)
    if not os.path.exists(exam_path):
        ui.warn(f"exam file not found: {exam_path}")
        return
    with open(exam_path) as fh:
        exam = yaml.safe_load(fh)
    ids = exam.get("scenarios") or []
    minutes = int(exam.get("minutes", 120))
    all_scen = {s.id: s for s in load_scenarios()}

    ui.banner(f"EXAM MODE  |  {len(ids)} questions  |  {minutes} min  |  threshold 66%")
    timer = Timer()
    results: list[ScenarioResult] = []
    total = 0.0
    for i, sid in enumerate(ids, 1):
        if sid not in all_scen:
            ui.warn(f"scenario '{sid}' missing — skipped")
            continue
        ui.info(f"=== Question {i}/{len(ids)} ===")
        total += all_scen[sid].weight
        r = run_scenario(all_scen[sid], backend, exam_timer=timer)
        results.append(r)
        if timer.elapsed() > minutes * 60:
            ui.warn("time limit reached, stopping exam")
            break

    report(results, total, timer.fmt())


def cmd_up(args):
    if not kubectl_installed():
        ui.warn("kubectl not installed. See install.sh")
        return
    if not kind_installed():
        ui.warn("kind not installed. Run:  bash install.sh")
        return
    backend.create()
    ui.ok("cluster ready: " + str(backend.ready()))


def cmd_down(args):
    backend.destroy()


def cmd_reset(args):
    if not _require_ready():
        return
    backend.reset()
    ui.ok("cluster state reset")


def cmd_status(args):
    print("kubectl:", "ok" if kubectl_installed() else "MISSING")
    print("kind:    ", "ok" if kind_installed() else "MISSING")
    print("cluster: ", "ready" if backend.ready() else "not running")


def build_parser():
    p = argparse.ArgumentParser(prog="cka-sim", description="CKA exam simulator (local kind)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list available scenarios").set_defaults(func=cmd_list)
    sp = sub.add_parser("run", help="run a single scenario")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("exam", help="run a full timed exam")
    sp.add_argument("--exam", default="full-exam.yaml")
    sp.set_defaults(func=cmd_exam)

    sub.add_parser("up", help="create the kind cluster").set_defaults(func=cmd_up)
    sub.add_parser("down", help="delete the kind cluster").set_defaults(func=cmd_down)
    sub.add_parser("reset", help="reset cluster state between questions").set_defaults(func=cmd_reset)
    sub.add_parser("status", help="show cluster/tooling status").set_defaults(func=cmd_status)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
