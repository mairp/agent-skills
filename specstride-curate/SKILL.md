---
name: "specstride-curate"
description: "Curate and reconcile a Spec Kit spec corpus for a target host: run the deterministic reconciliation script (backup, cross-artifact checks, per-feature logs), apply the curation prompt's retargeting rules with research agents, and refresh analyze reports. Auto-curation + auto-research."
compatibility: "Requires a specs/ corpus of numbered feature dirs with spec.md/plan.md/tasks.md; scripts/reconcile-specs.sh and prompts/curate-for-dsh.md in the repo (create them from the templates below if absent)."
metadata:
  author: "specstride-dsh"
  source: "prompts/curate-for-dsh.md"
---


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). `$ARGUMENTS` may name:
- a target host (default: dsh), a subset of features (`--feature NNN`), or `--dry-run`.

## Goal

One skill that performs, end to end, the auto-curation + auto-research loop over a spec corpus:

1. **Research** — verify host extension facts (plugin model, UI injection points, theming tokens) and any aesthetic reference; persist briefs under `research/` with citations and `unverified` markers.
2. **Reconcile (deterministic)** — run `scripts/reconcile-specs.sh`: backup to `.specstride/backups/<ts>/`, per-feature cross-artifact checks (test-name→task coverage, unresolved markers, dangling cross-feature refs, header fields, analyze-report presence), corpus summary `specs/RECONCILIATION.md`, append-only `specs/<feature>/reconciliation.md` logs.
3. **Curate (semantic)** — apply the curation prompt (`prompts/curate-for-dsh.md`) to the features the triage marks retarget-heavy or light-edit, fanning out subagents over disjoint feature sets; every change logged in the feature's `reconciliation.md`.
4. **Re-verify** — re-run the reconcile script; failures must be zero or explicitly waived in the log.

## Operating Constraints

- **Never destroy**: the script backs up before writing; curation never deletes a spec — de-prioritization is a Status change plus a note.
- **Preserve discipline**: provenance, dated facts, out-of-scope owner tables, stated constitution deviations. New host facts cite `research/` briefs or are marked `unverified` with the check that would settle them.
- **Disjoint writes**: parallel curation agents must own disjoint feature directories; the shared corpus summary is written only by the script.
- **Analysis before editing**: read each feature's `analyze-report.md` findings; apply or explicitly waive each open finding, and record which in `reconciliation.md`.

## Execution Steps

### 1. Ground the corpus

- Inventory `specs/` (feature dirs, artifacts present, analyze-report findings status). Classify each feature: host-coupling (none/light/heavy), relevance to the target plugin, open CRITICAL/HIGH count, recommended action (keep-as-is / light-edit / retarget / de-prioritize).
- If no triage exists, do it now (batch greps per feature: host mentions in spec headers, findings tables in analyze-report.md).

### 2. Ground the host (auto-research)

- Verify the target host's extension facts from its installed checkout/docs (structure, manifest, UI injection/slots, theming tokens, server services, example plugins). Persist as `research/<host>-plugin-facts.md`.
- If an aesthetic reference repo is named (e.g. a kanban to make beautiful), distill its data model + visual system into `research/<ref>-blueprint.md` with file:line citations.
- Fan out subagents for these two briefs in parallel when the corpora are large.

### 3. Run the deterministic reconcile

```bash
scripts/reconcile-specs.sh --dry-run   # inspect first
scripts/reconcile-specs.sh             # backup + write logs + corpus summary
```

If the script is missing, recreate it from the canonical behaviors in the Goal section (backup → checks a–e → summary + logs; exit nonzero on failures).

### 4. Fan out the semantic curation

- One agent authors any genuinely missing feature the corpus already cross-references (the corpus's own reserved slots win over new numbering).
- One agent retargets the heavy-coupling features.
- One agent applies light edits, settles open HIGH findings at their root cause, and de-prioritizes deferred adapters.
- Every agent: minimal diffs, corpus conventions, `reconciliation.md` entry per feature (`## reconcile-<date>` + bullets).

### 5. Re-verify and report

- Re-run `scripts/reconcile-specs.sh`; confirm zero failures or waivings recorded.
- Refresh `specs/RECONCILIATION.md` (the script does this) and summarize to the user: features touched, findings settled, new specs authored, open risks (`unverified` facts, waived findings).

## Operating Principles

- Deterministic checks are the script's job; semantic judgment is the agents' job; never mix them in one write.
- Rerunning without changes must be idempotent (append-only logs except the regenerated corpus summary).
- Report zero issues gracefully; report blocked research as `unverified` facts with settling checks, never as silence.

## Context

$ARGUMENTS
