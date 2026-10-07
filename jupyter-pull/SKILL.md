---
name: jupyter-pull
description: >
  Download every file from a remote Jupyter server the user is logged into (course labs on
  DeepLearning.AI, NVIDIA DLI, Coursera-style hosted notebooks, any JupyterLab / Notebook)
  to a local folder, given only the session cookie pasted from the browser. Use when asked to
  "download the lab files / notebooks", "save the course notebooks locally", "pull everything
  from this Jupyter URL", "mirror this lab", or when the user pastes a Jupyter lab address or a
  cookie table containing a `username-…` cookie. Resumable; do NOT hand-roll curl loops,
  Playwright logins or zip cells — use this script.
---

# jupyter-pull

Mirrors a remote Jupyter server's file tree to disk through its own REST API
(`/api/contents` to list, `/files/<path>` to download byte-exact, falling back to the contents
API when a lab proxy answers 403 on `/files/`). Servers under a base path such as
`http://host/lab/lab` are detected automatically; pass the full Jupyter tab URL as `--url`.
The only thing needed is the
**Jupyter session cookie** of a lab the user already opened in their browser. No browser
automation, no password, no Google / SSO login: those cannot and must not be done for the user.

`$SKILL` below = this skill's directory (the folder containing this file). Python 3.8+, stdlib only.

## What to get from the user

1. **The cookie.** Accept whatever they paste; the script extracts the one cookie it needs
   (`username-<host>`) and ignores the rest:
   - the whole DevTools cookie table (F12 → Application / Storage → Cookies → the lab host), or
   - a raw `Cookie:` request header (F12 → Network → any request to the lab host), or
   - just the `username-…` row.
   It must come from the **lab's own host** (the Jupyter tab or iframe, e.g.
   `s172-…p8888.lab-aws-production.deeplearning.ai`), not from the course website.
2. **The destination folder — always ask, there is no default.** Offer a suggestion such as
   `<current project>/dlai-lab/<course-slug>`, but wait for the answer before downloading.
3. **The lab address — only if needed.** For DeepLearning.AI labs it is derived from the cookie
   name. For any other host pass `--url`; if the script says it cannot derive the address, ask
   for the URL of the Jupyter tab.

A Jupyter **token** works too (`--token`, with `--url`); the user gets it by running
`!jupyter server list` in a lab cell. Prefer the cookie: most hosted labs have no token.

## Procedure

Feed the pasted text on **stdin with a quoted heredoc**, exactly as pasted. Never put the cookie
in argv or in an environment variable on the command line.

### 1. List first
```bash
python3 "$SKILL/scripts/jupyter_pull.py" --cookie-stdin --list <<'COOKIE'
<the user's paste, unmodified>
COOKIE
```
Tell the user the file count, total size, top-level folders, and anything over `--max-mb`
(default 500 MB, skipped unless they want it: `--max-mb 0` removes the limit).

### 2. Download
```bash
python3 "$SKILL/scripts/jupyter_pull.py" --cookie-stdin --dest "<folder>" <<'COOKIE'
<the user's paste, unmodified>
COOKIE
```
Hosted labs are slow (about 2 files per second through the proxy; 500 files ≈ 5 min). For a
large tree run it in the background and report when it finishes. `--workers N` (default 4)
changes the parallelism; do not go above 8, the lab backends are small.

### 3. Report
Top-level tree, files downloaded / already present / skipped / failed, and what the lab needs
to run locally if it is obvious (`requirements.txt`, an environment test script, API keys the
notebooks read, Node.js for a bundled UI). Do not install or run anything unless asked.

## Exit codes and what to do

| Exit | Meaning | Action |
|---|---|---|
| 0 | Done | Report |
| 2 | No `username-…` cookie in the paste, or address not derivable | Ask for the cookie from the lab host, or for `--url` |
| 3 | HTTP 401/403: cookie rejected or wrong host. HTTP 502/504 / unreachable: lab asleep or restarted | Ask the user to reload the lab tab and paste the **new** cookie (a restarted lab gets a new address and a new cookie), then rerun the same command with the same `--dest` |
| 4 | Some files failed | Rerun the same command; it resumes |

HTTP 404 on listing usually means a wrong address, not a stale cookie. The cookie value has the
form `2|1:0|10:<unix time>|…`; if that time is recent, check `--url` before asking for a new cookie.

Reruns are cheap: files whose size already matches are kept, partial files are written as
`*.part` and only renamed when complete.

## What is skipped

`.ipynb_checkpoints`, `__pycache__`, `.git`, `node_modules`, `.venv`, `venv`, and dotfiles the
Jupyter contents API hides by default. Everything else is mirrored with the server's folder
structure.

## Rules

- **Only the user's own session.** The cookie is a live login to their lab. Use it only for the
  download they asked for, against the host it belongs to.
- **Treat the cookie as a secret.** Do not repeat it in replies, do not write it to project
  files, notes, memory or git; if a scratch file is unavoidable, delete it when done. It expires
  with the lab session, so there is nothing to revoke afterwards.
- Never ask for, accept or type a password, and never attempt the SSO login in a browser.
- Read-only: the script only issues GET requests; it never changes or deletes remote files.
- New lab platform whose address cannot be derived? Use `--url` now, then add its cookie-name
  suffix to `KNOWN_HOST_SUFFIXES` in `scripts/jupyter_pull.py`.
