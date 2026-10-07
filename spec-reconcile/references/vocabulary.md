# Vocabulary

These are the only words allowed in the `Kind`, `Verdict`, `Severity` and `Action`
cells of a reconciliation sheet. Nothing else may appear in those cells — not a
synonym, not a qualifier, not a hedge. Everything a row needs to say beyond these
words belongs in the Claim, Deployed fact or Owner cell, where prose is expected.

## Kinds — seven

- `requirement` — a functional or non-functional requirement (an FR or NFR).
- `decision` — a decision recorded in the plan or in the research.
- `task` — a task marked done.
- `contract` — an interface or a schema.
- `disclosure` — a simulation the specification says is labelled.
- `measurement` — a number the specification records.
- `registry` — a status or milestone row.

## Verdicts — six

- `holds` — the deployed fact matches the claim.
- `holds, undocumented` — the deployment does what the specification says and more; the
  more is not in any specification.
- `drifted` — the deployment differs from the claim; the claim was true once (cite the
  run or commit where it held).
- `never held` — the claim was not true at the specification's close either.
- `unverifiable` — no surface can answer it read-only; say which surface would.
- `superseded` — a later specification or amendment changed the claim and the registry
  says so.

Two rules bind the verdict column and are not negotiable:

1. A verdict with no dated, cited deployed fact is not written down. `unverifiable` is a
   valid cell, and its Deployed fact cell names the surface that would answer the claim
   and the read that would do it.
2. A `drifted` row must cite the run or commit where the claim held. If that citation
   cannot be opened and read, the row is `never held`, not `drifted`.

## Severities — three

- `blocking` — a constitution principle or a disclosure is violated, or a status row
  asserts something false.
- `material` — a reader of the specification would build or operate the wrong thing.
- `cosmetic` — wording, or a stale number that changes no decision.

## Actions — nine

- `amend spec`
- `amend plan`
- `amend tasks`
- `amend contract`
- `amend registry`
- `amend constitution (PATCH|MINOR|MAJOR)` — keep exactly one of the three levels, taken
  from the project's governance rules; where the project has no constitution, this action
  does not apply.
- `spawn spec`
- `fix deployment` — the skill records it; it never does it.
- `none`

The skill proposes actions and writes them on the sheet. It applies none of them: it
does not amend, does not append tasks, and does not touch a deployment.
