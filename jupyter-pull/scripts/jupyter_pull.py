#!/usr/bin/env python3
"""Mirror every file of a remote Jupyter server (course lab, JupyterLab, Notebook) locally.

  jupyter_pull.py --cookie-stdin [--url URL] --list            # what is there, how big
  jupyter_pull.py --cookie-stdin [--url URL] --dest DIR        # download / resume

Auth, one of:
  --cookie-stdin      read a pasted cookie from stdin, in any of these shapes:
                        * the browser DevTools cookie table (name <tab> "value" per line)
                        * a raw "Cookie: a=b; c=d" request header
                        * just the  username-<host>  line
                      Only the Jupyter session cookie (username-*) is kept; the rest is dropped.
  --cookie-file PATH  same content, from a file
  --token TOKEN       a Jupyter token (or env JUPYTER_TOKEN)

The lab address is taken from --url, or derived from the cookie name for known lab hosts.
Walks /api/contents, downloads through /files/<path> (byte-exact; falls back to the contents
API in base64 when a proxy blocks /files/), retries 5xx answers, and skips files already
complete, so a rerun after a dropped session resumes. A server under a base path
(e.g. http://host/lab/lab) is found by also trying the URL with only its last /lab stripped.
Exit codes: 0 ok, 2 usage / cookie problem, 3 auth rejected or server unreachable, 4 some files failed.
"""
import argparse
import concurrent.futures
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SKIP_DIRS = {".ipynb_checkpoints", "__pycache__", ".git", "node_modules", ".venv", "venv"}

# cookie-name suffix (host with every non-alphanumeric turned into "-") -> real domain
KNOWN_HOST_SUFFIXES = {
    "-lab-aws-production-deeplearning-ai": ".lab-aws-production.deeplearning.ai",
}


def parse_cookie(text):
    """Return (name, value) of the Jupyter session cookie found in pasted text."""
    m = re.search(r"(username-[A-Za-z0-9-]+)\s*[=\t ]\s*(.+)", text)
    if not m:
        return None, None
    name, value = m.group(1), m.group(2).strip()
    value = value.split(";")[0].strip() if value.count('"') < 2 else value
    # DevTools wraps the value in '...' ; Jupyter's own value keeps its "..." quotes
    if len(value) >= 2 and value[0] == value[-1] == "'":
        value = value[1:-1]
    m2 = re.match(r'^("[^"]*")', value)
    if m2:
        value = m2.group(1)
    elif not value.startswith('"'):
        value = '"' + value.split()[0].strip('"') + '"'
    return name, value


def url_from_cookie_name(name):
    host = name[len("username-"):]
    for suffix, domain in KNOWN_HOST_SUFFIXES.items():
        if host.endswith(suffix):
            return "https://" + host[: -len(suffix)] + domain
    return None


class Client:
    def __init__(self, base, headers):
        self.base, self.headers = base, headers

    def open(self, path, tries=5, query=""):
        url = self.base + urllib.parse.quote(path) + query
        for attempt in range(tries):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                return urllib.request.urlopen(req, timeout=120)
            except urllib.error.HTTPError as e:
                # 5xx from the lab proxy is transient; auth errors are not
                if e.code < 500 or attempt == tries - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == tries - 1:
                    raise
            time.sleep(2 * (attempt + 1))

    def walk(self, path=""):
        with self.open("/api/contents/" + path) as r:
            listing = json.load(r)
        for item in sorted(listing["content"], key=lambda i: i["path"]):
            if item["type"] == "directory":
                if item["name"] not in SKIP_DIRS:
                    yield from self.walk(item["path"])
            else:
                yield item["path"], item.get("size")

    def fetch(self, rel, dest):
        target = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        part = target + ".part"
        try:
            with self.open("/files/" + rel) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        except urllib.error.HTTPError as e:
            # some proxies block /files/ but allow the contents API; raw bytes come back base64-encoded
            if e.code not in (403, 404):
                raise
            with self.open("/api/contents/" + rel, query="?type=file&format=base64&content=1") as r:
                data = base64.b64decode(json.load(r)["content"])
            with open(part, "wb") as f:
                f.write(data)
        os.replace(part, target)
        return os.path.getsize(target)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="lab address (…/tree, …/lab or bare); optional for known lab hosts")
    ap.add_argument("--dest", help="local folder to download into")
    ap.add_argument("--list", action="store_true", help="only list remote files and sizes")
    ap.add_argument("--cookie-stdin", action="store_true")
    ap.add_argument("--cookie-file")
    ap.add_argument("--token", default=os.environ.get("JUPYTER_TOKEN"))
    ap.add_argument("--max-mb", type=float, default=500, help="skip files larger than this (default 500; 0 = no limit)")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if not a.list and not a.dest:
        ap.error("give --dest DIR, or --list")

    headers, base = {"User-Agent": "Mozilla/5.0"}, a.url
    if a.cookie_stdin or a.cookie_file:
        text = sys.stdin.read() if a.cookie_stdin else open(a.cookie_file, encoding="utf-8").read()
        name, value = parse_cookie(text)
        if not name:
            print("No Jupyter session cookie (username-…) found in the pasted text.", file=sys.stderr)
            sys.exit(2)
        headers["Cookie"] = f"{name}={value}"
        base = base or url_from_cookie_name(name)
        if not base:
            print(f"Cannot derive the address from cookie '{name}'; pass --url.", file=sys.stderr)
            sys.exit(2)
    elif a.token:
        headers["Authorization"] = "token " + a.token
    else:
        ap.error("give --cookie-stdin, --cookie-file or --token")
    if not base:
        ap.error("--url is required with --token")
    raw = base.rstrip("/")
    # a lab served under a base path (e.g. host/lab/lab) needs only the last app segment stripped
    # try the minimal strip first: the bare host of a base-path lab can answer 502, not 404
    candidates = [re.sub(r"/(tree|lab|notebooks|login)(\?.*)?$", "", raw),
                  re.sub(r"/(tree|lab|notebooks|login)(/.*|\?.*)?$", "", raw)]
    candidates = list(dict.fromkeys(candidates))
    try:
        for i, base in enumerate(candidates):
            client = Client(base, headers)
            try:
                files = list(client.walk())
                break
            except urllib.error.HTTPError as e:
                if e.code not in (404, 502, 503, 504) or i == len(candidates) - 1:
                    raise
        print(f"server: {base}")
    except urllib.error.HTTPError as e:
        print(f"server: {base}")
        hint = "cookie / token rejected, or it belongs to another lab address" if e.code in (401, 403) else \
               "lab backend not answering (session asleep or restarted on a new address)"
        print(f"HTTP {e.code}: {hint}.", file=sys.stderr)
        sys.exit(3)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Server unreachable: {e}. The lab session probably ended; reload the lab and send the new cookie.", file=sys.stderr)
        sys.exit(3)

    total = sum(s or 0 for _, s in files)
    limit = a.max_mb * 1024 * 1024
    if a.list:
        for rel, size in files:
            print(f"  {human(size or 0):>10}  {rel}")
        print(f"\n{len(files)} files, {human(total)}")
        big = [(r, s) for r, s in files if limit and (s or 0) > limit]
        if big:
            print(f"Over --max-mb {a.max_mb:g} (would be skipped): " + ", ".join(f"{r} ({human(s)})" for r, s in big))
        return

    todo, kept, skipped = [], 0, []
    for rel, size in files:
        target = os.path.join(a.dest, rel)
        if size is not None and os.path.exists(target) and os.path.getsize(target) == size:
            kept += 1
        elif limit and (size or 0) > limit:
            skipped.append(f"{rel} ({human(size)})")
        else:
            todo.append(rel)
    print(f"{len(files)} remote files ({human(total)}): {len(todo)} to download, {kept} already present")

    done, nbytes, failed = 0, 0, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        futures = {pool.submit(client.fetch, rel, a.dest): rel for rel in todo}
        for fut in concurrent.futures.as_completed(futures):
            rel = futures[fut]
            try:
                size = fut.result()
                done, nbytes = done + 1, nbytes + size
                print(f"  {human(size):>10}  {rel}")
            except Exception as e:  # noqa: BLE001 - report and keep going
                failed.append(f"{rel} ({e})")

    print(f"\n{done} downloaded ({human(nbytes)}), {kept} already present -> {os.path.abspath(a.dest)}")
    if skipped:
        print(f"Skipped, larger than --max-mb {a.max_mb:g}:\n  " + "\n  ".join(skipped))
    if failed:
        print("Failed (rerun to resume):\n  " + "\n  ".join(failed))
        sys.exit(4)


if __name__ == "__main__":
    main()
