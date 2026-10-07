---
name: proxmox-triage
description: >
  Read-only diagnosis of Proxmox guests on the mairp host. Use when asked to
  "diagnose a VM/LXC", "is guest X up", "why is <service> unreachable",
  "what's running on this Proxmox host", "list the VMs/containers", or to check
  node/storage health. Observe-and-report only — it never changes guest state.
---

# Proxmox triage (read-only)

You are diagnosing Proxmox guests on host **mairp**. Use the guarded wrapper `pvectl`
(`/root/proxmox-ops/pvectl.sh`) — never raw `qm`/`pct`. Everything here is read-only.

## Commands (all safe, no state change)

```
/root/proxmox-ops/pvectl.sh list              # all guests: id/name/type/status/node
/root/proxmox-ops/pvectl.sh status <id>       # one guest: status + config summary
/root/proxmox-ops/pvectl.sh config <id>       # full guest config
/root/proxmox-ops/pvectl.sh health            # node status + storage + guest counts
/root/proxmox-ops/pvectl.sh snapshots <id>    # snapshot list
```

Add `--json` to any of the above for machine-readable output.

## HARD RULES

- **Read-only.** Do NOT run `start/stop/reboot/shutdown/snapshot/restore/delsnap/backup/onboot`
  here — those belong to the `proxmox-ops` skill and require explicit confirmation. If the user
  asks for a state change, hand off to `proxmox-ops`, don't improvise with raw `qm`/`pct`.
- **Diagnose in order:** for an unreachable guest, run `pvectl status <id>` FIRST (is it even
  running?) before assuming a network/service problem.
- Report concisely: guest id/name, status, and the one or two config lines that matter
  (onboot, net0, memory/cores). No emojis.

## Known facts (host mairp)

- **VM 101 `cws-v1.1`** runs Cisco YANGSuite on **:8480** (`onboot: 1`). If YANGSuite is
  unreachable, check `pvectl status 101` first — the guest must be `running`.
- **VM 100 `k3s-node`** is normally stopped.
- The **PVE host firewall is disabled** on this box — do not attribute guest reachability
  problems to PVE firewall rules; look at the guest and its in-guest service instead.
- Node name is **mairp**; storage/health via `pvectl health`.
