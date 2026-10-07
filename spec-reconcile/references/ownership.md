# The ownership ladder

A claim enumerated from a specification is owned by that specification at **rung 0**;
its Owner cell reads `<spec id> (rung 0)`. Everything else — every deployed fact that no
enumerated claim mentions — goes through the ladder below.

Four rungs, tried in order. The first that resolves wins. **Every candidate is recorded
in the Owner cell even when a later rung decides**, in the form:

```
002 (rung 3; rung-1 candidates 001, 002, 003)
```

and, where nothing resolves, in the form `unowned → <spec id> by surface`.

Every rung is executable with `git` and file reads alone. No rung needs a running
system, a build, or a tool the project does not already carry.

## Step 0 — the id-range check, once per run

This is a step the skill performs, never an assumption it makes. Before any bare
identifier is used as evidence at rung 2:

- Read the **first and last task id** of every `tasks.md` in the repository.
- Read the **first and last requirement id** of every `spec.md` in the repository.
- Write both ranges, per specification, into the sheet header.

If the task ranges restart (every list beginning at the same first id) or the
requirement ranges overlap between specifications, then **a bare task or requirement
number without a specification id is not evidence at rung 2** for the rest of the run,
and the sheet header says so in one line. If every range is globally unique and
disjoint, a bare id *is* evidence at rung 2, and the header says that instead.

## Rung 1 — direct reference

A specification artefact names the thing. Grep the specification folders for the exact
identifier, path, key, endpoint or container name the deployed fact carries, then rank
the hits by specificity:

- a **contract** naming the exact key, endpoint or container beats
- a **task** naming the file, which beats
- a **plan** naming the directory.

One candidate at the highest specificity present: that specification is the owner, at
rung 1. Several candidates at the same specificity: carry all of them to rung 2 and keep
them in the Owner cell for the rest of the ladder.

## Rung 2 — commit trail

Find the commit that introduced the fact, then read the specification out of that commit:

```
git log --follow -- <file>
git blame -L <line>,<line> -- <file>
git show --stat <sha>
```

Then, **in this order**, accept the first form of evidence the commit offers:

1. **A scope prefix that is a specification id** — a subject beginning `002:` or
   `002 …`. A prefix that is a plain word (`config:`, `docs:`, `fix:`) is not evidence.
2. **A specification-qualified id in the body** — `002 T314`, or a requirement id whose
   range step 0 proved unambiguous. A bare task or requirement number is evidence only
   if step 0 proved the ranges globally unique.
3. **The branch the commit merged from**, when the branch is named after a specification
   folder. Read it from the merge subject:

   ```
   git log --merges --first-parent
   ```

   A subject of the form `Merge branch '<spec-folder-name>'` names the specification
   branch as the source; a subject of the form `Merge main into <spec-folder-name>`
   names it as the target. **Either direction names the specification branch**, and the
   specification folder embedded in the name is the candidate. Where the specification
   branches still exist:

   ```
   git branch --contains <sha>
   ```

   and take the **earliest specification branch that contains the commit** — earliest by
   the branch's own first commit date, not by listing order. A commit contained by every
   branch (because it landed on the trunk and was merged outward) resolves nothing here.

If no form of evidence applies, carry the candidates to rung 3.

## Rung 3 — registry precedence

When two or more specifications still claim the same surface, the project's registry
decides, where it has a **Completes** column or a milestone table: the specification that
**completed the milestone owns the runtime behaviour**, and the earlier specification
owns the **schema or the shape**. Split the fact if both are in play: the value of a key
and the way the running product behaves go to the completer; the existence of the key,
its type and its position in the file go to the earlier specification. Record the split
as two rows with the same Deployed fact and different Owners.

Where the project has no registry, the **latest closed specification that names the
surface** owns it, and the Owner cell says so: `003 (rung 3; no registry, latest closed
naming the surface)`.

## Rung 4 — unowned

Nothing resolves. The row goes on the sheet of the specification **whose contract governs
the surface the fact was read from** — a lane configuration to the specification holding
the lane contract, a user-interface bundle to the user-interface specification, a schema
file to the specification holding the data model. The row takes:

- verdict `holds, undocumented`,
- action `amend contract` where a contract exists and should have named it, or
  `spawn spec` where the fact is large enough to be its own piece of work,
- Owner cell `unowned → <spec id> by surface`.

A fact that lands here and is **not** the surface of any contract in the repository goes
to the "Candidate specs" section of the sheet with action `spawn spec`, and the Owner
cell reads `unowned → none by surface`.

## Handing a row to another sheet

When the ladder assigns a fact to a specification other than the one being reconciled,
the fact does not become a row on this sheet. It is listed in the sheet's "Handed to the
root" section with its Owner cell, its dated deployed fact and the rung that decided, so
that the specification's own reconciliation picks it up. The reverse direction is
answered either way: every deployed fact read during the run ends up either as a row, as
a handed-over line, or as a candidate specification.
