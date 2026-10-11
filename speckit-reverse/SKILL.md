---
name: speckit-reverse
description: Reverse-engineer an existing codebase (a git repo, a dirty worktree, or a plain directory at a local path) into a complete as-is Spec Kit feature (constitution, spec, requirements checklist, plan, research, data model, contracts, quickstart and ticked tasks) with `specstride reverse`, then hand the result to mixture-of-loops as a launch-contract baseline. Use whenever someone wants Spec Kit / speckit artifacts, a spec, or a baseline "for what already exists", asks to "reverse engineer", "document as-is", "retro-spec", "specify an existing repo/project/folder", "bootstrap spec-kit for a legacy codebase", or wants Specstride or mixture-of-loops to run on a project that has no specs yet, even if they don't say "reverse".
---

# Spec Kit reverse engineering (Specstride + mixture-of-loops)

Turn a directory as it exists today into a Spec Kit feature directory that describes it,
then hand that baseline to mixture-of-loops. This is description work: the product is never
changed, built, tested or run, and the source directory gets exactly one new directory
(`specs/NNN-as-is-<slug>/`) and nothing else, unless the user asks for more.

The work splits the way the tools do:

- **Specstride** (`specstride reverse`) writes the artifacts, one gate per phase, and a
  deterministic linter plus a source guard decide each gate. A critic model also judges.
- **mixture-of-loops** (MoL) then takes the finished feature as its input and derives a
  provenance-bound launch contract, so later runs (converge, extend, re-verify) start from
  a baseline instead of from nothing.
- **`scripts/reverse_kit.py`** (next to this file; call its directory `SKILL_ROOT`) does
  every deterministic step, so the traps below are handled by code, not by memory.

## Why a frozen snapshot, and the traps the script handles

Reverse cites source lines, and a run lasts 20 to 90 minutes. If the source changes during
the run, citations go stale and the guard fails gates. So the script reverse-engineers a
**snapshot**: a separate git repository whose HEAD is exactly the content being described,
at one SHA that every citation is pinned to. It also:

- calls the real `specstride` binary, never the interactive shell function (that function
  appends `-w`, which `reverse` refuses). Set `SPECSTRIDE_BIN` if it is not on `PATH`.
- numbers the feature itself (one past the highest `specs/NNN-*` in the source), so copying
  it back cannot collide with an existing feature.
- writes the launch log **beside** the snapshot, never inside it. A growing file inside the
  snapshot would enter the inventory and fail every gate on the guard.
- passes no `--no-color` (the orchestrator rejects it and the run dies at once).
- refuses when the snapshot directory already exists (it may hold a run to resume) or when
  the source already has an `as-is-<slug>` feature. Ask the user in both cases; don't delete.

## Choosing the snapshot

| Target | `--snapshot` | What gets described |
| --- | --- | --- |
| git repo root, clean | `auto` (= `head`) | the checked-out commit |
| git repo root, dirty, user says "as committed", "main", a branch or tag | `head` or `ref:REF` (e.g. `ref:origin/main`) | that commit |
| git repo root, user says "my working copy", "including my changes", "what's on disk" | `worktree` | HEAD plus tracked edits, untracked non-ignored files and deletions, committed inside the snapshot |
| subdirectory of a repo | automatic | that subtree's working files |
| plain directory (no git) | automatic | all files except `.git`, `node_modules`, `.venv`, `dist`, `build` and caches; a copied `.gitignore` is honoured |

When a repo is dirty and the request doesn't say which state it means, use `head` (reproducible
and citable) and say in the report that uncommitted changes were left out and `--snapshot
worktree` would include them.

## Workflow

Run each step as a shell command and read its output. `PLAN` is the `*.plan.json` path
`prepare` prints; the later steps only need it. Where a step calls `specstride` directly
(`status`, `stop`, `resume`, `feedback`), use the binary path in the plan's `specstride` field
and the plan's `work` as `WORK`, never the shell function.

### 1. Prepare (no LLM call)

```bash
python3 SKILL_ROOT/scripts/reverse_kit.py prepare SRC [--name SLUG] [--snapshot MODE] [--root DIR] [-- EXTRA_FLAGS]
```

The slug names the feature (`NNN-as-is-<slug>`) and the run (`reverse-<slug>`), so it should
be the project's name, not wherever it happens to be checked out. Without `--name` the script
takes the first of: a manifest's package name (`pyproject.toml`, `package.json`, `Cargo.toml`,
`setup.cfg`, `go.mod`), the `origin` remote's repository name, a README title of at most four
words, and only then the directory name. `prepare` prints `slug` and `name_source`. Pass
`--name` when the user names the project, and when `name_source` is `directory name` and that
name is generic (`src`, `app`, `work`, `fixture`, a date): read the README or code for the real
name. Say in the report where the name came from.

Snapshots default to `~/speckit-reverse/<slug>-<sha7>/` (`--root` or `SPECKIT_REVERSE_ROOT`
overrides; it must be outside the source). `EXTRA_FLAGS` pass through to `specstride reverse`
(e.g. `--proposer`, `--critic`, `--max-rejects`) — only when the user asked for them; otherwise
Specstride's own `.env` defaults choose the models.

It prints the dry run and checks it: output dir, tasks mode, at least five phases ending in the
cross-artifact analysis (more when the source is oversize and phase 1 is split per unit),
`SPECSTRIDE_GIT_COMMITS=off`, `--feature reverse-<slug>`, a nonzero inventory, and that the dry
run changed nothing but `.specstride/`. Exit 4 means a check failed: report it and stop. Tell
the user the inventory line (files, bytes, units) and whether a constitution will be written
(`to be written` means the source has no `.specify/memory/constitution.md`; the one reverse
writes lives in the feature's `memory/` and describes the code, never replacing a project
constitution).

If the user asked only for a plan or dry run, stop here.

### 2. Launch detached

```bash
python3 SKILL_ROOT/scripts/reverse_kit.py launch --plan PLAN
```

It starts the run in its own session with stdin closed, confirms the orchestrator is alive,
and prints the run header (proposer, critic, timeouts, run_id).

### 3. Supervise, read-only

Don't poll in a tight loop and don't touch anything in the snapshot while the run is live:
the guard fails a gate on any change outside the output and state directories. Wait in the
background with the script, which returns at the next critic verdict or when the run ends:

```bash
python3 SKILL_ROOT/scripts/reverse_kit.py wait --plan PLAN            # next verdict
python3 SKILL_ROOT/scripts/reverse_kit.py wait --plan PLAN --until-exit --max-minutes 180
```

Run it as a background command when the harness supports that, and tell the user what phase
is running between waits. After the **first** verdict, look at the line `wait` prints for it:

- an empty reply, a parse failure, or a transport error is an `infra` problem, not a spec
  problem: stop the run (`specstride stop -w WORK`) and report it rather than letting it grind.
- "reply is the verdict line only" is not an error, but it means the approval carries no
  reasoning; say so in the report, because the spot-checks then carry more weight.

Once the first verdict looks sound, `--until-exit` is enough.

### 4. When it stops

`specstride status -w WORK --feature reverse-<slug>` shows the state.

- **DONE, all approved**: continue.
- **Stopped on a transient or infra error**: `specstride resume -w WORK --feature reverse-<slug>`,
  at most twice, saying what happened before each resume. `resume` keeps git commits off.
- **A gate rejected at its limit, or halted**: read `specstride feedback <N> -w WORK --feature
  reverse-<slug>` and the lint output, then stop and report. Never hand-edit artifacts to force
  a pass: the value of the baseline is that the gates, not you, accepted it.

### 5. Verify independently

```bash
python3 SKILL_ROOT/scripts/reverse_kit.py verify --plan PLAN
python3 SKILL_ROOT/scripts/reverse_kit.py claims --plan PLAN [--focus WORD …]
```

`verify` re-runs the linter at `--upto 5` against the snapshot, confirms HEAD didn't move and
nothing outside `specs/` and `.specstride/` changed, finds `ANALYSIS.md`, and prints the
counts and any recorded contradictions. Exit 5 means one of those failed. Read `ANALYSIS.md`.

The linter proves structure and that every citation exists; it cannot prove a claim is true.
`claims` prints a sample (3 FR, 2 SC, 2 research Decisions, 1 data-model entity) with the
lines each cites. Judge every one: does the cited code actually say this? Use `--focus` with
words for the product's core behaviour so the sample hits what matters, and read beyond the
printed excerpt (`sed -n` in the snapshot) when a claim spans more than it shows. A claim the
lines don't support goes in the report; don't fix it.

### 6. Bring the feature back

```bash
python3 SKILL_ROOT/scripts/reverse_kit.py bring-back --plan PLAN
```

It copies the feature to `SRC/specs/NNN-as-is-<slug>/` (refusing to overwrite), lints the copy
against the snapshot, and reports whether `specs/` is gitignored there. Don't `git add`, commit,
branch or push, and don't put anything else (a README, notes) in the feature directory: the
linter fails on stray files. Keep the snapshot: its `.specstride/reverse/<slug>/` holds the
inventory, driver, `ANALYSIS.md` and run state, and the citations resolve against it.

### 7. Hand off to mixture-of-loops

Invoke the `mixture-of-loops` skill (or follow its SKILL.md, usually at
`~/.claude/skills/mixture-of-loops/` or `~/.agents/skills/mixture-of-loops/`) with the source
as the repository and `specs/NNN-as-is-<slug>` as the feature, in **generate** mode. Every
task in the baseline is already ticked, so the contract it derives describes and re-verifies
existing work; it is the starting point for a later converge or extension, not a build.

- Pass the request so MoL's own mode reader sees no execution words: this skill never runs the
  MoL launcher. Offer `run` as a next step only.
- For a git source, ask MoL to put its ignore rules in `.git/info/exclude`, not `.gitignore`,
  so this description-only job leaves shared files untouched — unless the user said otherwise.
- If MoL's bootstrap or validation stops on a blocker, report it; that is normal for a draft.

Skip this step only when the user asked for the Spec Kit artifacts alone.

## Report

Keep it short, in this order:

1. Source, snapshot mode, snapshot SHA (and source HEAD if different), snapshot path, feature path.
2. Per gate: time, rejections, and any resumes; the critic transport and whether its replies had reasoning.
3. Lint result (errors, warnings) and each `ANALYSIS.md` finding in one line.
4. Spot-check table: claim, citation, supported yes/no (with what's missing when no).
5. Counts: user stories, FR, SC, tasks, contracts, `[NEEDS CLARIFICATION]` markers.
6. Contradictions between the as-is artifacts and the project's own docs (README, contributor
   docs, an existing constitution): list them, don't fix them.
7. The MoL outcome: contract path, status, open blockers, and the next step offered.
