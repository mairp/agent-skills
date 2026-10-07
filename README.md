# agent-skills

Agent skills I use every day on my host, shared as-is. Each directory is a skill in the
de-facto Agent Skills format: a `SKILL.md` with YAML frontmatter (`name`, `description`)
plus whatever scripts and references the skill needs.

They are written for [Claude Code](https://code.claude.com/docs/en/skills), which loads
them from `~/.claude/skills/<name>`, but the format is plain Markdown + Bash/Python and
works with any harness that reads the same layout (Codex `~/.agents/skills`, dsh
`~/.dsh/skills`, pi `~/.pi/agent/skills`, …). Skills that reference my own host's paths
(`/root/gpu_rtx_3090`, `fleet.sh`, llama-swap) say so in the skill itself — swap the paths
for yours.

## The skills

| Skill | What it does |
|---|---|
| [gpu-ops](gpu-ops/) | Operate and inspect an RTX 3090 eGPU in a Thunderbolt-4 enclosure: status, free VRAM, drain, safe power off/up, detach — through proven scripts, never ad-hoc commands. |
| [fleet-control](fleet-control/) | Bring the LLM/observability stack up or down (`fleet.sh`), check the eGPU, get an observability digest. |
| [proxmox-ops](proxmox-ops/) | Guarded lifecycle operations on Proxmox guests (start, stop, snapshot, rollback, backup); destructive actions require an explicit `--yes`. |
| [proxmox-triage](proxmox-triage/) | Read-only diagnosis of Proxmox guests: is it up, why is a service unreachable, node/storage health. Observe-and-report only. |
| [local-model-ops](local-model-ops/) | Hardware-aware guidance for local Qwen/Muse/Nemotron models on one RTX 3090: which model, when to think, when to escalate to a hosted frontier model. |
| [qmd-recall](qmd-recall/) | Recall from and write to the shared fleet memory (qmd) — prior context, past decisions, durable gotchas for every agent on the host. |
| [spec-reconcile](spec-reconcile/) | Read a spec folder and the deployed surfaces read-only, then write a dated spec-vs-deployed sheet in a fixed vocabulary. Ships a vocabulary, a sheet template, an ownership table and evals. |
| [jupyter-pull](jupyter-pull/) | Download every file from a remote Jupyter server you are logged into (course labs, DLI, Coursera-style notebooks), given only the browser session cookie. |
| [specstride-curate](specstride-curate/) | Curate and reconcile a Spec Kit spec corpus for a target host — unattended end to end: auto-research agents verify the target host's extension facts and distill aesthetic references into cited briefs, a deterministic script backs up and cross-checks the corpus, then curation agents apply the retargeting rules and analyze reports are refreshed. |

Companion repos: [gpu_rtx_3090](https://github.com/mairp/gpu_rtx_3090) (the GPU scripts
gpu-ops drives), [qmd-gateway](https://github.com/mairp/qmd-gateway) (the memory gateway
qmd-recall talks to), [claude-plugins](https://github.com/mairp/claude-plugins)
(`speckit-batch`), [mixture-of-loops](https://github.com/mairp/mixture-of-loops)
(`specstride-batch`).

## Install

Symlink (not copy) so the skill stays where it is and edits land in one place:

```bash
git clone https://github.com/mairp/agent-skills ~/.local/share/agent-skills
ln -s ~/.local/share/agent-skills/gpu-ops ~/.claude/skills/gpu-ops
# repeat per skill, or:
for d in ~/.local/share/agent-skills/*/; do ln -s "$d" ~/.claude/skills/"$(basename "$d")"; done
```

Skills are curated per session through `skillOverrides` in a Claude Code settings
profile, so nothing loads unless the session asks for it.
