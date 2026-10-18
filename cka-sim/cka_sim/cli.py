"""CLI entry point: list / run / exam / review / tagged / tag / untag / up / down / reset / status."""
from __future__ import annotations

import argparse
import os
import sys

import yaml

from cka_sim import review, ui
from cka_sim.cluster import KindBackend, kind_installed, kubectl_installed
from cka_sim.engine import (
    NavRequest,
    ScenarioResult,
    SessionExit,
    load_scenarios,
    run_scenario,
)
from cka_sim.paths import EXAMS_DIR
from cka_sim.reporter import report
from cka_sim.timer import Timer

backend = KindBackend()


def cmd_list(args):
    scen = load_scenarios()
    if not scen:
        ui.warn("no scenarios found in scenarios/")
        return
    n_tagged = sum(1 for s in scen if review.is_tagged(s.id))
    print(f"{'id':28} {'domain':22} {'weight':>6} {'diff':8} title")
    print("-" * 96)
    for s in scen:
        star = " ★" if review.is_tagged(s.id) else ""
        print(f"{s.id:28} {s.domain:22} {s.weight:>6} {s.difficulty:8} {s.title}{star}")
    if n_tagged:
        print("-" * 96)
        ui.info(f"{n_tagged} tagged for review  →  ./run.sh tagged  |  ./run.sh review")


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
    try:
        run_scenario(scen[args.id], backend)
    except SessionExit:
        return
    except NavRequest:
        ui.warn("navigation (:back/:goto) works inside sessions — ./run.sh exam | ./run.sh review")


def _print_progress(seq, results, current):
    print()
    ui.info(f"session map — {len(seq)} questions  ([✓] passed  · attempted  → current  ★ tagged)")
    for n, sid in enumerate(seq, 1):
        r = results.get(sid)
        mark = "✓" if r and r.passed else ("·" if r else " ")
        here = "→ " if n - 1 == current else "  "
        star = " ★" if review.is_tagged(sid) else ""
        print(f"  {here}{n:>2}. [{mark}] {sid}{star}")
    print()


def _session_loop(ids, minutes=None):
    """Run a sequence of scenarios with :back / :goto <n> / :exit navigation.

    Scoring rule: the first PASSED attempt sticks; a scenario that was failed
    or skipped gets its result replaced by a later (better) revisit.
    """
    all_scen = {s.id: s for s in load_scenarios()}
    seq = [s for s in ids if s in all_scen]
    missing = [s for s in ids if s not in all_scen]
    for m in missing:
        ui.warn(f"scenario '{m}' missing — skipped")
    if not seq:
        ui.warn("nothing to run")
        return

    timer = Timer()
    results: dict = {}
    i = 0
    while 0 <= i < len(seq):
        sid = seq[i]
        nav_help = "  (:back" if i > 0 else "  (:goto n"
        if i > 0:
            nav_help += " :goto n :exit)"
        else:
            nav_help += " :exit)"
        ui.info(f"=== Question {i + 1}/{len(seq)} ==={nav_help}   ★=tagged  :goto sans n° = carte")
        try:
            r = run_scenario(all_scen[sid], backend, exam_timer=timer if minutes else None)
        except SessionExit:
            ui.warn("session interrupted — partial report")
            break
        except NavRequest as nav:
            if nav.listing:
                _print_progress(seq, results, i)
                continue
            j = i + nav.target if nav.relative else nav.target - 1
            if not (0 <= j < len(seq)):
                ui.warn(f"question out of range 1..{len(seq)}")
                continue
            i = j
            continue
        prev = results.get(sid)
        if prev and prev.passed and not r.passed:
            ui.info(f"'{sid}' already passed earlier — first PASS kept for the score")
        else:
            results[sid] = r
        i += 1
        if minutes and timer.elapsed() > minutes * 60:
            ui.warn("time limit reached, stopping session")
            break

    ordered = [results[sid] for sid in seq if sid in results]
    total = sum(all_scen[sid].weight for sid in seq)
    report(ordered, total, timer.fmt())


def cmd_exam(args):
    if not _require_ready():
        return
    exam_path = os.path.join(EXAMS_DIR, args.exam)
    if not os.path.exists(exam_path):
        ui.warn(f"exam file not found: {exam_path}")
        return
    with open(exam_path) as fh:
        exam = yaml.safe_load(fh)
    ids = exam.get("scenarios") or []
    minutes = int(exam.get("minutes", 120))
    threshold = int(exam.get("threshold", 66))
    ui.banner(f"EXAM MODE  |  {len(ids)} questions  |  {minutes} min  |  threshold {threshold}%")
    _session_loop(ids, minutes=minutes)


def cmd_tagged(args):
    items = review.tagged()
    if not items:
        ui.info("no tagged scenarios — use :tag inside a scenario, or ./run.sh tag <id>")
        return
    all_scen = {s.id: s for s in load_scenarios()}
    print(f"{'id':28} {'tagged':17} note")
    print("-" * 90)
    for sid, info in items:
        when = info.get("tagged_at", "?").replace("T", " ")
        note = info.get("note", "")
        known = "" if sid in all_scen else "  (missing!)"
        print(f"{sid:28} {when:17} {note}{known}")
    print("-" * 90)
    ui.info(f"{len(items)} tagged  →  ./run.sh review  (file: ~/.cache/cka-sim/review.json)")


def cmd_review(args):
    if not _require_ready():
        return
    ids = [sid for sid, _ in review.tagged()]
    if not ids:
        ui.info("nothing tagged for review yet — use :tag inside a scenario")
        return
    ui.banner(f"REVIEW MODE  |  {len(ids)} tagged scenario(s)  |  no timer")
    _session_loop(ids, minutes=None)


def cmd_tag(args):
    review.tag(args.id, args.note)
    extra = f"  note: {args.note}" if args.note else ""
    ui.hint(f"★ tagged for review: {args.id}{extra}")


def cmd_untag(args):
    review.untag(args.id)
    ui.hint(f"un-tagged: {args.id}")


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

    sub.add_parser("list", help="list available scenarios (★ = tagged for review)").set_defaults(func=cmd_list)
    sp = sub.add_parser("run", help="run a single scenario")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("exam", help="run a full timed exam (:back/:goto to navigate)")
    sp.add_argument("--exam", default="full-exam.yaml")
    sp.set_defaults(func=cmd_exam)

    sub.add_parser("tagged", help="list scenarios tagged for review").set_defaults(func=cmd_tagged)
    sub.add_parser("review", help="re-run all tagged scenarios (revision queue)").set_defaults(func=cmd_review)

    sp = sub.add_parser("tag", help="tag a scenario for review")
    sp.add_argument("id")
    sp.add_argument("--note", default=None)
    sp.set_defaults(func=cmd_tag)

    sp = sub.add_parser("untag", help="remove the review tag")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_untag)

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
