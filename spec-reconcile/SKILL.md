---
name: "spec-reconcile"
description: "Reconcile spec with what is actually deployed: read a specification folder and one or more deployment surfaces read-only, then write a dated sheet of spec vs deployed rows in a fixed vocabulary. Use when asked to reconcile spec and reality, audit drift between spec and deployment, check whether a closed specification still describes the running product, or attribute a deployed thing back to the specification that owns it."
argument-hint: "<spec-folder> [--against <surface>…] [--date YYYY-MM-DD]"
compatibility: "Any repository holding a specification folder (Spec Kit shape, or any folder with a spec.md) plus read access to at least one deployment surface"
metadata:
  author: "project"
  source: "~/.claude/skills/spec-reconcile"
user-invocable: true
disable-model-invocation: false
---

# Spec Reconcile

Check a written specification against the world that was built from it, and write the
result down as evidence rather than as an opinion.

Given a specification folder and one or more deployment surfaces, this skill enumerates
every claim the specification makes, reads what is deployed, matches the two, and writes
`<spec-folder>/reconciliation-<date>.md` — one row per claim, one row per deployed fact
no claim covers, each row carrying a dated citation on both sides.

Resolve relative resources from the directory holding this `SKILL.md`; call it
`SKILL_ROOT`. Do not depend on a host-specific variable, hook, subagent or tool name.
Read `SKILL_ROOT/references/vocabulary.md` (the only words allowed in the Kind, Verdict,
Severity and Action cells), `SKILL_ROOT/references/sheet-template.md` (the output shape)
and `SKILL_ROOT/references/ownership.md` (the ladder) before step 1.

## How this differs from the two neighbouring skills

- `/speckit-converge` assesses the codebase and **appends unbuilt work to `tasks.md`**;
  this skill never writes tasks and never writes into the specification during a run.
- `/speckit-analyze` checks the specification **against itself** (spec, plan and tasks
  for internal consistency); this skill checks the specification **against the world**.

## Command line

`/spec-reconcile <spec-folder> [--against <surface>…] [--date YYYY-MM-DD]`

- `<spec-folder>` — a folder with a `spec.md`; a Spec Kit feature set (`spec.md`,
  `plan.md`, `tasks.md`, `contracts/`, `research.md`, run logs) uses all of it.
- `--against <surface>` — repeatable. A path, a service name, a URL or a git range. With
  none given, discover surfaces the specification's own artefacts name and list what was
  discovered in the sheet header; never widen the scope silently.
- `--date YYYY-MM-DD` — the date stamped on the sheet and on every fact. Defaults to
  today. Every fact is dated with the date it was **read**, not the date it was written.

## Deployment surfaces

A deployment surface is anything readable that says what is deployed. The known kinds,
each with its read-only read and the deployed fact it yields:

| Surface kind | Read it with | Deployed fact |
| --- | --- | --- |
| Container composition file | file read | the declared services, images, networks, mounts, environment, secrets |
| Running containers | `docker ps`, `docker inspect <name>` | what actually runs, from which image and digest, since when, with which environment and mounts |
| A file an image carries | `docker exec <name> cat <path>` | the constant, list or template the running image holds |
| Container output | `docker logs --tail <n> <name>` | startup banners, resolved configuration, refusals |
| Orchestrator namespace | the cluster CLI's `get`/`describe` in read verbs only | workloads, images, replicas, config maps |
| Service self-report | `curl` to a health, about or version endpoint | the version, build, feature list or identifier list the service admits to |
| Configuration directory | file reads | the keys and values the product starts from |
| Git range | `git log`, `git show`, `git diff --stat`, `git blame` | what changed since the specification closed, and who introduced it |
| Runbook or tutorial | file read | the procedure an operator is told to follow |
| Infrastructure state file | file read | the declared resources |
| Package manifest with lockfile | file read | the pinned dependency versions |

**Read-only is absolute.** The skill never mutates a surface: no composition command, no
build, no restart, no write into a running container, no test run that changes state, no
scaling, no rollout. The allowed reads are exactly: `docker ps`, `docker inspect`,
`docker logs --tail`, `docker exec … cat <file>` to read a file the image carries,
`curl` to a health, about or version endpoint, `git` in its read verbs, and reading
files. A finding that says the deployment is wrong is a row with the action
`fix deployment`, never a command the skill runs. Where an endpoint needs a credential,
read the credential from wherever the project keeps it, use it in the request, and never
write it — nor any token, password or key material — into the sheet, the summary or a
log; the sheet cites the endpoint and the date, not the secret.

## Steps

**1 — Enumerate the claims.** Walk the specification folder and collect every claim it
makes, each with `file:line` and the quoted text: every functional and non-functional
requirement; every task marked done; every contract, interface and schema; every
decision recorded in the plan or the research; every disclosure the specification says
is labelled; every measurement, number or threshold it records; and every registry or
status row elsewhere in the repository that speaks about this specification. A claim
that cannot be quoted with a line number is not a claim; drop it and say so in the
header. Count them — the count drives the fan-out decision below.

**2 — Read the surfaces.** Read each surface named by `--against`, or discovered, with
the read-only reads above, and record for each one the exact command or file path that
read it and the date. Reading a surface produces deployed facts, each of which is itself
citable: a service name and image digest, a key and its value, an identifier list, a
version string, a commit sha. Facts that were read are written down whether or not a
claim turns out to need them; a surface listed in the header with no facts under it is a
surface that answered nothing, and the sheet says so.

**2b — Resolve ownership.** Every deployed fact that no enumerated claim mentions is run
through the four-rung ladder in `SKILL_ROOT/references/ownership.md`, which answers the
reverse direction — deployed thing to specification — with `git` and file reads alone.
The ladder's rung 2 depends on whether the project's identifiers are global; perform its
id-range check once per run, as a step, before using a bare identifier as evidence.
Record every candidate in the Owner cell even when a later rung decides, and hand a fact
the ladder assigns to another specification to that specification's sheet through the
"Handed to the root" section rather than writing it here.

**3 — Match claims to facts.** One row per claim, one row per unowned deployed fact,
nothing merged and nothing dropped. Each row takes exactly one verdict, one severity and
one action from `SKILL_ROOT/references/vocabulary.md`. A verdict with no dated, cited
deployed fact on the row is not written down: use `unverifiable`, and name in the
Deployed fact cell the surface that would answer it and the read that would do so. A
`drifted` row must cite the run, commit or dated artefact where the claim did hold; if
that citation cannot be opened and read, the row is `never held`, not `drifted`.
Deployed facts that no claim covers become `holds, undocumented` rows on the sheet the
ladder assigned them to.

**4 — Group the rows into the amendment list.** Group by action, and under each action
list the row numbers and what the amendment must say. Where the project has a
constitution at `.specify/memory/constitution.md`, read its governance section and cite
the rule each amendment answers to, including its amendment level where the governance
defines levels, and carry whatever that governance demands in the same change (rationale,
migration impact, updated conformance evidence, the companion files it names). Where the
project has no constitution, record the action with no level and say in the header that
no governance document was found. The skill proposes amendments; it does not apply them.

**5 — Write the sheet.** Write `<spec-folder>/reconciliation-<date>.md` from
`SKILL_ROOT/references/sheet-template.md`: the header block, the table with its fixed
columns, "Amendments by action", "Handed to the root", "Candidate specs". Writing this
one file is the only write the skill performs.

**6 — Print a ten-line summary.** Ten lines to the terminal: the specification id and
its close commit; the date and the surfaces read; the claim count; the count per verdict;
the blocking rows by number with their action; the rows handed to another specification;
the candidate specifications; and the path of the sheet.

## Fan-out

One agent can hold roughly 150 claims with their citations. Above that, split by kind —
requirements to one agent, tasks and runs to a second, contracts and decisions to a
third, disclosures, measurements and registry rows to a fourth — give each the same
vocabulary, sheet template and read-only rule, have each return rows in the table's
column order with its own row numbering prefixed by its kind, then merge: renumber
sequentially, resolve two agents claiming the same fact through the ownership ladder
rather than by preferring either agent, and name in the header which tier produced which
section. Subagents are never required; a single agent doing the kinds in sequence
produces the same sheet.

## Worked example of the ladder

A deployment's lane configuration carries a key that governs how requests are shaped for
one model lane. The value changed after every specification in the repository had closed.
Rung 1, direct reference: three specifications' task lists name that configuration file,
so the file yields three candidates rather than an owner, and all three are carried
forward. Rung 2, commit trail: `git blame` of the line resolves to a commit whose subject
is prefixed with a plain `config:` scope, whose body names no specification, and which
landed directly rather than through a merge from a specification branch — no evidence at
this rung, and the run's id-range check has already shown that a bare task number would
not be evidence either, because task numbering restarts in every task list. Rung 3,
registry precedence: the registry's "Completes" column says which specification completed
the data-path milestone of the earliest plan, and that specification owns the runtime
behaviour of the lane, while the earlier specification keeps the schema and the shape of
the file. The Owner cell records the outcome and the discarded candidates together, in
the form `<winner> (rung 3; rung-1 candidates <a>, <b>, <c>)`.

## Eval

`SKILL_ROOT/evals/` holds one end-to-end case with its expected rows; see
`SKILL_ROOT/evals/README.md` for the command and what each expected row proves.
