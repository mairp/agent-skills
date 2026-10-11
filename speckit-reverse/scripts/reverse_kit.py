#!/usr/bin/env python3
"""Deterministic plumbing for reverse-engineering a directory into an as-is Spec Kit feature.

Subcommands (every one after `prepare` takes --plan, the JSON `prepare` writes):

  prepare   SRC [--name SLUG] [--snapshot auto|head|worktree|ref:REF] [--root DIR] [-- EXTRA…]
            freeze SRC into a git snapshot at one SHA, pick the feature number, run
            `specstride reverse --dry-run` and check what it prints
  launch    start the run detached, with its log beside (never inside) the snapshot
  wait      block until a new critic verdict lands or the run ends (--until-exit: only the end)
  verify    lint --upto 5, HEAD unchanged, no stray change, ANALYSIS.md present
  claims    print a sample of evidence-bearing claims with the lines they cite
  bring-back  copy the feature into SRC/specs/ and lint the copy

Nothing here writes to SRC except `bring-back`, which only adds one new directory.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".tox", ".mypy_cache", ".pytest_cache", ".specstride", "target", ".next"}
SNAP_IDENT = ["-c", "user.name=speckit-reverse", "-c", "user.email=snapshot@speckit-reverse.local",
              "-c", "commit.gpgsign=false"]


def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run(argv, cwd=None, check=True, env=None) -> str:
    out = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env)
    if check and out.returncode != 0:
        die(f"{' '.join(map(str, argv))} exited {out.returncode}: {(out.stderr or out.stdout).strip()[:500]}")
    return out.stdout


def git(args, cwd, check=True) -> str:
    return run(["git", *SNAP_IDENT, *args], cwd=cwd, check=check)


def specstride_bin() -> str:
    # Never the interactive shell function: it appends `-w`, which `reverse` refuses.
    for cand in (os.environ.get("SPECSTRIDE_BIN"), shutil.which("specstride"),
                 str(Path.home() / "specstride" / "specstride")):
        if cand and os.access(cand, os.X_OK) and Path(cand).is_file():
            return cand
    die("specstride binary not found; set SPECSTRIDE_BIN")


def kebab(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:40] or "source"


def strip_noise(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if "setlocale" not in l)


def project_name(src: Path) -> tuple[str, str]:
    """The project's own name, in order of how much it can be trusted."""
    def first(pattern, text):
        m = re.search(pattern, text, re.M)
        return m.group(1).strip() if m else None
    manifests = (("pyproject.toml", r'^name\s*=\s*["\']([^"\']+)'),
                 ("package.json", r'^\s*"name"\s*:\s*"([^"]+)"'),
                 ("Cargo.toml", r'^name\s*=\s*"([^"]+)"'),
                 ("setup.cfg", r'^name\s*=\s*(\S+)'),
                 ("go.mod", r'^module\s+(\S+)'))
    for fname, pattern in manifests:
        f = src / fname
        if f.is_file():
            n = first(pattern, f.read_text(errors="replace"))
            if n:
                return n.rsplit("/", 1)[-1].lstrip("@"), fname
    top = git_top(src)
    if top == src:
        url = subprocess.run(["git", "-C", str(src), "remote", "get-url", "origin"],
                             capture_output=True, text=True).stdout.strip()
        if url and not Path(url).is_dir():
            return re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]), "git remote"
    for readme in ("README.md", "README.rst", "README.txt", "README"):
        f = src / readme
        if f.is_file():
            title = first(r"^#\s+(.+?)\s*#*$", f.read_text(errors="replace"))
            if title:
                title = re.sub(r"[`*_\[\]]", "", title).strip()
                if 0 < len(title.split()) <= 4:
                    return title, readme
    return src.name, "directory name"


# ── snapshot ────────────────────────────────────────────────────────────────────

def git_top(src: Path) -> Path | None:
    out = subprocess.run(["git", "-C", str(src), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    return Path(out.stdout.strip()).resolve() if out.returncode == 0 else None


def copy_files(src: Path, dst: Path, rels) -> int:
    n = 0
    for rel in rels:
        s = src / rel
        if s.is_symlink() or not s.is_file():
            continue
        d = dst / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        n += 1
    return n


def snapshot(src: Path, work: Path, mode: str) -> dict:
    """Make WORK a git repo whose HEAD is exactly what will be reverse-engineered."""
    top = git_top(src)
    info = {"source": str(src), "snapshot_mode": None, "source_head": None, "dirty": None}
    if top is not None and top == src:
        head = run(["git", "-C", str(src), "rev-parse", "HEAD"]).strip()
        dirty = bool(run(["git", "-C", str(src), "status", "--porcelain"]).strip())
        info.update(source_head=head, dirty=dirty)
        if mode == "auto":
            mode = "head"          # committed state: reproducible and citable
        ref = mode[4:] if mode.startswith("ref:") else "HEAD"
        sha = run(["git", "-C", str(src), "rev-parse", "--verify", f"{ref}^{{commit}}"]).strip()
        run(["git", "clone", "-q", str(src), str(work)])
        if subprocess.run(["git", "-C", str(work), "cat-file", "-e", sha]).returncode != 0:
            # e.g. origin/main or a detached HEAD: not among the refs a clone copies
            full = run(["git", "-C", str(src), "rev-parse", "--symbolic-full-name", ref]).strip()
            git(["fetch", "-q", str(src), full or sha], work)
        git(["checkout", "-q", "--detach", sha], work)
        info["ref"] = ref
        if mode == "worktree":
            # overlay the working tree: tracked edits, untracked non-ignored files, deletions
            rels = run(["git", "-C", str(src), "ls-files", "-co", "--exclude-standard", "-z"]).split("\0")
            copy_files(src, work, [r for r in rels if r])
            for rel in run(["git", "-C", str(src), "ls-files", "--deleted", "-z"]).split("\0"):
                if rel and (work / rel).exists():
                    (work / rel).unlink()
            git(["add", "-A"], work)
            if git(["status", "--porcelain"], work).strip():
                git(["commit", "-q", "-m", f"speckit-reverse worktree snapshot of {src}"], work)
        info["snapshot_mode"] = mode
    else:
        # plain directory, or a subdirectory of a repo: copy the files, then make it a repo
        work.mkdir(parents=True)
        if top is not None:
            rels = run(["git", "-C", str(src), "ls-files", "-co", "--exclude-standard", "-z"]).split("\0")
            copy_files(src, work, [r for r in rels if r])
            info["snapshot_mode"] = "subdir-worktree"
            info["source_head"] = run(["git", "-C", str(top), "rev-parse", "HEAD"]).strip()
        else:
            for dirpath, dirnames, filenames in os.walk(src):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                rel_dir = Path(dirpath).relative_to(src)
                copy_files(src, work, [rel_dir / f for f in filenames])
            info["snapshot_mode"] = "plain"
        git(["init", "-q"], work)
        git(["add", "-A"], work)          # honours any copied .gitignore
        git(["commit", "-q", "--allow-empty", "-m", f"speckit-reverse snapshot of {src}"], work)
    info["sha"] = git(["rev-parse", "HEAD"], work).strip()
    if git(["status", "--porcelain"], work).strip():
        die(f"snapshot {work} is not clean after creation")
    return info


def next_number(src: Path, work: Path) -> str:
    nums = []
    for base in (src / "specs", work / "specs"):
        if base.is_dir():
            nums += [int(m.group(1)) for p in base.iterdir() if (m := re.match(r"^(\d{3})-", p.name))]
    return "%03d" % (max(nums, default=0) + 1)


def check_dry_run(text: str, out: Path, slug: str, tasks: str) -> list[str]:
    problems = []
    if f"output dir  : {out}" not in text:
        problems.append(f"output dir is not {out}")
    if f"tasks mode  : {tasks}" not in text:
        problems.append(f"tasks mode is not {tasks}")
    phases = re.findall(r"^\s+(\d+)\. (.+?)\s+\(lint --upto", text, re.M)
    if len(phases) < 5:
        problems.append(f"expected at least 5 phases, saw {len(phases)}")
    elif "Cross-artifact" not in phases[-1][1]:
        problems.append("last phase is not the cross-artifact analysis")
    orch = [l for l in text.splitlines() if "orchestrator.sh" in l]
    if not orch or "SPECSTRIDE_GIT_COMMITS=off" not in orch[-1]:
        problems.append("orchestrator line lacks SPECSTRIDE_GIT_COMMITS=off")
    if not orch or f"--feature reverse-{slug}" not in orch[-1]:
        problems.append(f"orchestrator line lacks --feature reverse-{slug}")
    m = re.search(r"inventory\s+: (\d+) text files.*?(\d+) bytes; oversize=(\w+); units=(\d+)", text)
    if not m or int(m.group(1)) == 0:
        problems.append("inventory saw no text files")
    return problems


def cmd_prepare(a) -> None:
    src = Path(a.src).expanduser().resolve()
    if not src.is_dir():
        die(f"{src} is not a directory")
    if a.name:
        slug, name_source = kebab(a.name), "--name"
    else:
        raw, name_source = project_name(src)
        slug = kebab(raw)
    root = Path(a.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if root == src or src in root.parents:
        die("--root must be outside the source")
    if (src / "specs").is_dir() and any(p.name.endswith(f"-as-is-{slug}") for p in (src / "specs").iterdir()):
        die(f"{src}/specs already holds an as-is-{slug} feature; ask before adding another", 3)
    stage = root / f".{slug}-{os.getpid()}"
    info = snapshot(src, stage, a.snapshot)
    work = root / f"{slug}-{info['sha'][:7]}"
    if work.exists():
        shutil.rmtree(stage)
        die(f"{work} already exists: it may hold a run to resume "
            f"(plan: {work}.plan.json). Ask before reusing or removing it.", 3)
    stage.rename(work)
    nnn = next_number(src, work)
    fname = f"{nnn}-as-is-{slug}"
    out = work / "specs" / fname
    ss = specstride_bin()
    argv = [ss, "reverse", str(work), "--name", slug, "--out", str(out), "--tasks", a.tasks, *a.extra]
    dry = strip_noise(run([*argv, "--dry-run"], cwd=work, check=False))
    problems = check_dry_run(dry, out, slug, a.tasks)
    stray = [l for l in git(["status", "--porcelain"], work).splitlines()
             if not l[3:].startswith(".specstride/")]
    if stray:
        problems.append("dry run changed the snapshot: " + ", ".join(stray))
    plan = {"slug": slug, "name_source": name_source, "feature": f"reverse-{slug}", "src": str(src), "work": str(work),
            "out": str(out), "feature_name": fname, "nnn": nnn, "specstride": ss,
            "argv": argv, "log": f"{work}.launch.log", **info,
            "dry_run_problems": problems, "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    Path(f"{work}.plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(dry)
    print("\n── prepare ──")
    for k in ("slug", "name_source", "src", "snapshot_mode", "dirty", "source_head", "sha", "work", "out", "log"):
        print(f"{k:14}: {plan[k]}")
    print(f"{'plan':14}: {work}.plan.json")
    if problems:
        print("DRY-RUN CHECK FAILED:\n  - " + "\n  - ".join(problems))
        sys.exit(4)
    print("dry-run check: ok")


# ── run control ─────────────────────────────────────────────────────────────────

def load(plan_path: str) -> dict:
    return json.loads(Path(plan_path).read_text())


def state_dir(p: dict) -> Path:
    return Path(p["work"]) / ".specstride" / "features" / p["feature"]


def orchestrator_alive(p: dict) -> bool:
    out = subprocess.run(["pgrep", "-f", f"orchestrator.sh -w {p['work']}( |$)"],
                         capture_output=True, text=True)
    return bool(out.stdout.strip())


def status_text(p: dict) -> str:
    return strip_noise(run([p["specstride"], "status", "-w", p["work"], "--feature", p["feature"]],
                           check=False))


def cmd_launch(a) -> None:
    p = load(a.plan)
    if p.get("dry_run_problems"):
        die("the dry run did not pass its checks; fix or ask before launching")
    if orchestrator_alive(p):
        die("a run is already active for this snapshot")
    if (state_dir(p) / "gates").is_dir():
        die("this slug already has gate state: use `specstride resume`, not a second launch")
    with open(p["log"], "ab") as log:
        subprocess.Popen(p["argv"], cwd=p["work"], stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(12):
        time.sleep(5)
        if orchestrator_alive(p):
            break
    text = strip_noise(Path(p["log"]).read_text(errors="replace"))
    if not orchestrator_alive(p):
        print(text[-3000:])
        die("the orchestrator is not running after launch; see the log above")
    print("\n".join(text.splitlines()[:25]))
    print(f"\nlaunched: log {p['log']}")


def verdict_files(p: dict) -> list[Path]:
    d = state_dir(p) / "verdicts"
    return sorted(d.glob("*.txt"), key=lambda f: f.stat().st_mtime) if d.is_dir() else []


def describe_verdict(f: Path) -> str:
    text = f.read_text(errors="replace")
    head = dict(re.findall(r"^(\w+): (.*)$", text.split("═", 1)[0], re.M))
    reply = text.split("REPLY", 1)[-1].strip("═ \n") if "REPLY" in text else ""
    body = [l for l in reply.splitlines() if l.strip() and not l.startswith("VERDICT ")]
    note = "reply is the verdict line only (no reasoning)" if not body else f"reply has {len(body)} lines of reasoning"
    if not reply.strip():
        note = "EMPTY REPLY: treat as infra"
    elif head.get("parse") not in (None, "ok"):
        note += f"; parse={head.get('parse')}: treat as infra"
    return (f"{f.name}: provider={head.get('provider')} verdict={head.get('verdict')} "
            f"parse={head.get('parse')} — {note}")


def cmd_wait(a) -> None:
    p = load(a.plan)
    seen = len(verdict_files(p))
    deadline = time.time() + a.max_minutes * 60
    while time.time() < deadline:
        vs = verdict_files(p)
        if not a.until_exit and len(vs) > seen:
            print("NEW VERDICT")
            for f in vs[seen:]:
                print("  " + describe_verdict(f))
            break
        if not orchestrator_alive(p):
            print("RUN ENDED")
            break
        time.sleep(a.interval)
    else:
        print(f"TIMEOUT after {a.max_minutes} min (the run may still be going)")
    st = status_text(p)
    print("\n".join(st.splitlines()[:14]))
    log = next(state_dir(p).glob("runs/*/run.log"), None) if state_dir(p).is_dir() else None
    if log:
        marks = [l for l in log.read_text(errors="replace").splitlines()
                 if re.match(r"^(=====|----- critic|APPROVED|REJECTED)", l)]
        print("\n".join(marks[-12:]))


def cmd_verify(a) -> None:
    p = load(a.plan)
    ok = True
    lint = subprocess.run([p["specstride"], "reverse", "--lint", p["out"], "--src", p["work"],
                           "--upto", "5", "--json"], cwd=p["work"], capture_output=True, text=True)
    try:
        findings = json.loads(strip_noise(lint.stdout))
    except json.JSONDecodeError:
        findings = {"errors": ["unparseable lint output: " + lint.stdout[:300]], "warnings": []}
    print(f"lint: {len(findings['errors'])} error(s), {len(findings['warnings'])} warning(s)")
    for kind in ("errors", "warnings"):
        for f in findings[kind]:
            print(f"  {kind[:-1]}: {f}")
    ok &= not findings["errors"]
    head = git(["rev-parse", "HEAD"], p["work"]).strip()
    print(f"HEAD: {head[:7]} (snapshot {p['sha'][:7]}) {'ok' if head == p['sha'] else 'MOVED'}")
    ok &= head == p["sha"]
    rel_out = os.path.relpath(p["out"], p["work"])
    stray = [l for l in git(["status", "--porcelain"], p["work"]).splitlines()
             if not (l[3:].startswith(".specstride/") or l[3:].startswith("specs/")
                     or rel_out.startswith(l[3:].rstrip("/")))]
    print("status: " + ("only specs/ and .specstride/" if not stray else "STRAY: " + ", ".join(stray)))
    ok &= not stray
    analysis = Path(p["work"]) / ".specstride" / "reverse" / p["slug"] / "ANALYSIS.md"
    print(f"analysis: {analysis if analysis.is_file() else 'MISSING'}")
    ok &= analysis.is_file()
    out = Path(p["out"])
    spec = (out / "spec.md").read_text() if (out / "spec.md").is_file() else ""
    tasks = (out / "tasks.md").read_text() if (out / "tasks.md").is_file() else ""
    print("counts: stories=%d FR=%d SC=%d tasks=%d unticked=%d contracts=%d needs_clarification=%d" % (
        len(re.findall(r"^### User Story", spec, re.M)), len(re.findall(r"^- \*\*FR-", spec, re.M)),
        len(re.findall(r"^- \*\*SC-", spec, re.M)), len(re.findall(r"^- \[[ xX]\] T\d{3}", tasks, re.M)),
        len(re.findall(r"^- \[ \] T\d{3}", tasks, re.M)),
        len(list((out / "contracts").glob("*.md"))) if (out / "contracts").is_dir() else 0,
        spec.count("[NEEDS CLARIFICATION")))
    for f in sorted(out.rglob("*.md")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if "<!-- evidence:" in line and "contradicts=none" not in line:
                print(f"contradiction recorded: {f.relative_to(out)}:{n}: {line.strip()[:220]}")
    sys.exit(0 if ok else 5)


EVIDENCE = re.compile(r"<!-- evidence: (.+?) \| kind=(\w+) \| confidence=([\d.]+)")


def collect_claims(out: Path) -> dict[str, list[tuple[str, str, str]]]:
    groups: dict[str, list] = {"FR": [], "SC": [], "Decision": [], "Entity": []}
    sources = {"spec.md": ("FR", "SC"), "research.md": ("Decision",), "data-model.md": ("Entity",)}
    for name, kinds in sources.items():
        f = out / name
        if not f.is_file():
            continue
        lines = f.read_text().splitlines()
        for i, line in enumerate(lines[:-1]):
            m = EVIDENCE.search(lines[i + 1])
            if not m:
                continue
            if "FR" in kinds and re.match(r"^- \*\*FR-\d+", line):
                kind = "FR"
            elif "SC" in kinds and re.match(r"^- \*\*SC-\d+", line):
                kind = "SC"
            elif "Decision" in kinds and "**Decision**" in line:
                kind = "Decision"
            elif "Entity" in kinds and line.startswith("### "):
                kind = "Entity"
            else:
                continue
            groups[kind].append((f"{name}:{i + 1}", line.strip(), m.group(1) + f" (kind={m.group(2)}, conf={m.group(3)})"))
    return groups


def cmd_claims(a) -> None:
    p = load(a.plan)
    groups = collect_claims(Path(p["out"]))
    want = {"FR": 3, "SC": 2, "Decision": 2, "Entity": 1}
    rng = random.Random(a.seed)
    focus = [w.lower() for w in (a.focus or [])]
    for kind, n in want.items():
        items = groups[kind]
        preferred = [c for c in items if any(w in c[1].lower() for w in focus)]
        rest = [c for c in items if c not in preferred]
        rng.shuffle(preferred)
        rng.shuffle(rest)
        for where, claim, ev in (preferred + rest)[:n]:
            print(f"\n══ {kind} — {where}\n{claim[:600]}\nevidence: {ev}")
            for cite in ev.split(" (kind=")[0].split(", "):
                m = re.match(r"^(.+?):(\d+)(?:-(\d+))?$", cite.strip())
                if not m:
                    continue
                path = Path(p["work"]) / m.group(1)
                lo, hi = int(m.group(2)), int(m.group(3) or m.group(2))
                if not path.is_file():
                    print(f"  ── {cite}: FILE MISSING")
                    continue
                src_lines = path.read_text(errors="replace").splitlines()
                shown = min(hi, lo + a.max_lines - 1)
                print(f"  ── {cite}" + (f" (first {a.max_lines} lines)" if shown < hi else ""))
                for k in range(lo, shown + 1):
                    if k <= len(src_lines):
                        print(f"  {k:5}  {src_lines[k - 1][:200]}")


def cmd_bring_back(a) -> None:
    p = load(a.plan)
    dest = Path(p["src"]) / "specs" / p["feature_name"]
    if dest.exists():
        die(f"{dest} already exists; not overwriting", 3)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(p["out"], dest)
    lint = subprocess.run([p["specstride"], "reverse", "--lint", str(dest), "--src", p["work"],
                           "--upto", "5"], cwd=p["work"], capture_output=True, text=True)
    print(strip_noise(lint.stdout + lint.stderr).strip())
    print(f"copied: {dest}")
    top = git_top(Path(p["src"]))
    if top:
        ign = subprocess.run(["git", "-C", str(top), "check-ignore", "-q", str(dest)]).returncode == 0
        print("git: " + ("specs/ is gitignored here; left untracked" if ign
                         else "untracked in the source repo; not added or committed"))
    sys.exit(lint.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("src")
    pr.add_argument("--name")
    pr.add_argument("--snapshot", default="auto",
                    help="auto (=head for a repo root) | head | worktree | ref:REF")
    pr.add_argument("--tasks", default="done", choices=("done", "open"))
    pr.add_argument("--root", default=os.environ.get("SPECKIT_REVERSE_ROOT", str(Path.home() / "speckit-reverse")))
    pr.add_argument("extra", nargs="*", help="after --: extra `specstride reverse` launch flags")
    pr.set_defaults(fn=cmd_prepare)
    for name, fn in (("launch", cmd_launch), ("verify", cmd_verify), ("bring-back", cmd_bring_back)):
        s = sub.add_parser(name)
        s.add_argument("--plan", required=True)
        s.set_defaults(fn=fn)
    w = sub.add_parser("wait")
    w.add_argument("--plan", required=True)
    w.add_argument("--until-exit", action="store_true")
    w.add_argument("--max-minutes", type=int, default=60)
    w.add_argument("--interval", type=int, default=30)
    w.set_defaults(fn=cmd_wait)
    c = sub.add_parser("claims")
    c.add_argument("--plan", required=True)
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--max-lines", type=int, default=40)
    c.add_argument("--focus", nargs="*", help="words that make a claim preferred for the sample")
    c.set_defaults(fn=cmd_claims)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
