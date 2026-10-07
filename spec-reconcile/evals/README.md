# Eval — spec 002 of this repository against what runs today

One case. It is the only place in this skill where this repository's names, paths,
container names and ports may appear; `SKILL.md` and `references/` stay general.

## The case

Reconcile the closed specification `specs/002-extproc-data-path/` (the ext_proc data
path, merged to `main` before 2026-09-13) against two deployment surfaces: the
composition file `deploy/docker-compose.sovereign.yml`, and the `/api/about` self-report
of the running policy service.

## The command

```
/spec-reconcile specs/002-extproc-data-path \
  --against deploy/docker-compose.sovereign.yml \
  --against sovereign-policy:/api/about \
  --date 2026-09-17
```

The `/api/about` surface is read in one of two read-only ways, and the sheet says which:

- `docker exec sovereign-policy cat <path>` on the file the running image carries that
  defines `DISCLOSURE_IDS` (`services/policy/api/about.py` in the tree), or
- `curl` to the endpoint with a person token from `deploy/secrets/`
  (`person-*.token`). The token is used in the request and **never printed**
  — not into the sheet, not into the summary, not into a log.

Expected output: `specs/002-extproc-data-path/reconciliation-2026-09-17.md`, and nothing
else written. No container is started, stopped, recreated or written to.

## The expected rows

**1 — `exception_register_store`, the disclosure appended in constitution v1.6.2.**
Kind `disclosure`, Owner `002 (rung 0)`. The deployed `DISCLOSURE_IDS` list carries the
id, so the row is **`holds`**, severity `cosmetic`, action `none`. The Deployed fact cell
carries the read that produced it and the date.

**2 — `killswitch_store`, the second disclosure appended in v1.6.2.** Same shape, same
verdict: **`holds`**. Both ids are present in the deployed list; a missing id here would
be a `blocking` row, because Principle VII makes a simulation without a disclosure a
violation.

**3 — task T409 (`specs/002-extproc-data-path/tasks.md:345`).** Kind `task`, Owner
`002 (rung 0)`. The task row's evidence note names `runs/live-t409-2026-09-13.md`. Two
further live runs of the same date exist in the folder,
`runs/live-t409-2026-09-13-2.md` and `runs/live-t409-2026-09-13-3.md`, and they carry the
decision the task closed on. The verdict is **`holds`** if the task row or the run index
(`runs/README.md`) names all three files, and **`drifted`** otherwise — with the
`drifted` row citing `runs/live-t409-2026-09-13.md` as the run where the claim did hold.
At the time this eval was written (2026-09-17) neither the task row nor the run index
names `-2.md` or `-3.md`, so the expected verdict is **`drifted`**, severity `material`,
action `amend tasks` (recorded; the skill does not write it).

**4 — the `redact` sidecar of `sidecars/classifier-igpu/docker-compose.yml`.** A deployed
service that runs beside the three classifier sidecars. Step 2b sends it through the
ladder. Rung 1: 002's `contracts/health-and-doctor.md` probes the `redact` sidecar's
`/healthz` and `contracts/live-runner.md` lists a `redact` fault, so a contract names the
container — one candidate, `002 (rung 1)`, and the verdict is **`holds`** if the
deployment matches what those contracts say. If no 002 plan, tasks or contract had named
it, the row would be **`holds, undocumented`** with action `amend contract`. Either
outcome is acceptable to the eval; the row must exist and must show which artefact
resolved it.

**5 — the `chat_template_kwargs` entry of `config/lanes.yaml`.** The line lists
`chat_template_kwargs` under `remove_when_non_default` for the Lane B adapter; it was
introduced by commit `68e766c` ("Lane B caller identity, and strip the qwen reasoning
kwarg on Lane B"), whose subject is prefixed `config:` and carries no spec id. No claim
in 002 mentions the key, so the ladder runs:

- **Rung 1** — all three specifications' `tasks.md` name `config/lanes.yaml`, and 001's
  `contracts/lane-adapter.md` and `contracts/extproc-filters.md` name it too. Three
  candidates: 001, 002, 003. No single owner.
- **Step 0** — task ids restart at `T001` in every `tasks.md` and the FR ranges overlap
  (001 FR-001–FR-156, 002 FR-044a–FR-246, 003 FR-301–FR-380), so a bare `T` or `FR`
  number is not evidence at rung 2 for this run.
- **Rung 2** — `git blame` reaches `68e766c`; the prefix is `config:`, the body names no
  specification, and the commit did not arrive through a merge from a specification
  branch. Nothing resolves.
- **Rung 3** — `specs/README.md`'s **Completes** column says 002 completes 001's **M2**,
  the data path. The lane's runtime behaviour therefore belongs to 002; the shape of the
  file stays with 001.

Expected Owner cell: **`002 (rung 3; rung-1 candidates 001, 002, 003)`**, verdict
`holds, undocumented`, action `amend contract` (the lane adapter contract should name the
key) — and, because the runtime value is 002's, the row stays on this sheet rather than
being handed over.

## What a failing run looks like

- A verdict cell with no dated citation beside it (the rule says such a row is not
  written; `unverifiable` naming the surface is the correct cell).
- A `drifted` row whose cited run cannot be opened (it should have been `never held`).
- Any word in a Kind, Verdict, Severity or Action cell that is not in
  `references/vocabulary.md`.
- A task appended to `tasks.md` (that is `/speckit-converge`, not this skill).
- Any command that changes the stack, or a token value anywhere in the output.
