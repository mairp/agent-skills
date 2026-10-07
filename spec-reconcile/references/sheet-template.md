# Sheet template

The skill writes exactly one file per run: `<spec-folder>/reconciliation-<date>.md`.
Copy the shape below. The column set is fixed: do not add, drop, reorder or rename a
column, and put nothing in the Kind, Verdict, Severity or Action cells that is not in
`references/vocabulary.md`.

---

```markdown
# Reconciliation — <spec id> <spec title> — <YYYY-MM-DD>

**Specification.** <spec-folder>, closed at <close commit sha> (<subject>, <date>).
**Date of this sheet.** <YYYY-MM-DD>. Every fact below was read on this date unless the
cell says otherwise.

**Surfaces read.** Each with the command or file that read it, read-only:

| Surface | Kind | Read by | Read on |
| --- | --- | --- | --- |
| <name> | <surface kind> | `<exact command or file path>` | <YYYY-MM-DD> |

Credentials used for an endpoint read are named by their location only; no token,
password or key material appears anywhere in this sheet.

**Governance.** <the constitution path and the governance rules cited below, or: no
constitution found; actions are recorded without an amendment level>.

**Identifier ranges (step 0).** <per specification, the first and last task id and the
first and last requirement id>. <One line: whether a bare id is evidence at rung 2.>

**Agent tiers.** <which tier produced which section, or: single agent, all sections>.

**Summary.** <One paragraph: how many claims were enumerated; how many hold; the counts
for each other verdict; the blocking rows by number; how many deployed facts were handed
to another specification; how many candidate specifications came out.>

## Rows

| # | Claim (spec file:line, quoted) | Kind | Owner (spec id, rung) | Deployed fact (surface, how read, dated) | Verdict | Severity | Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `spec.md:214` "<quoted claim>" | requirement | 002 (rung 0) | composition file `<path>` line <n>, read <date> | holds | cosmetic | none |
| 2 | — (deployed fact with no claim) | contract | 002 (rung 3; rung-1 candidates 001, 002, 003) | `<command>` → `<value>`, read <date> | holds, undocumented | material | amend contract |

## Amendments by action

### amend spec
- Rows <n>, <n>: <what the amendment must say>. <Governance rule cited, with level.>

### amend plan
### amend tasks
### amend contract
### amend registry
### amend constitution (PATCH|MINOR|MAJOR)
### spawn spec
### fix deployment
- Rows <n>: <what is wrong in the deployment and what would put it right>. Recorded
  only; this skill changed nothing.

### none
- Rows <n>, <n>.

## Handed to the root

Deployed facts the ownership ladder assigned to a different specification. They are not
rows above; they belong on that specification's sheet.

| Deployed fact (surface, how read, dated) | Owner (spec id, rung) | Why |
| --- | --- | --- |

## Candidate specs

`holds, undocumented` rows large enough to be their own piece of work, and facts the
ladder left at `unowned → none by surface`.

| Row / fact | What it is | Proposed scope | Action |
| --- | --- | --- | --- |
```

---

## Notes on filling it

- **`#`** — sequential from 1 across the whole table. Under fan-out, each agent numbers
  its rows with a kind prefix and the merge renumbers sequentially.
- **Claim** — `file:line` plus the quoted text, short enough to read in the table and
  long enough to be recognisable. A deployed fact with no claim uses `—`.
- **Kind** — one of the seven kinds.
- **Owner** — `<spec id> (rung <n>[; rung-1 candidates <a>, <b>, …])`, or
  `unowned → <spec id> by surface`.
- **Deployed fact** — the surface, the exact command or file path that read it, the
  value read, and the date. A row with no dated, cited fact here takes the verdict
  `unverifiable` and names the surface that would answer it.
- **Verdict**, **Severity**, **Action** — one word (or one action phrase) each, from
  the vocabulary.
- A `drifted` row carries, in the Deployed fact cell, the run or commit where the claim
  did hold; if that citation cannot be opened, the row is `never held`.
