---
name: proxmox-ops
description: >
  Guarded lifecycle operations on Proxmox guests (VMs and LXC) on the mairp host:
  start, stop, reboot, shutdown, snapshot, restore/rollback, delete snapshot,
  backup, and set onboot. Use when asked to change a guest's state or protect it
  before a risky change. Destructive actions require explicit --yes confirmation.
---

# Proxmox lifecycle ops (guarded)

You operate Proxmox guests on host **mairp** through the guarded wrapper `pvectl`
(`/root/proxmox-ops/pvectl.sh`) — never raw `qm`/`pct`. State changes are **gated**: without
`--yes`, `pvectl` prints the exact command + a one-line impact and does nothing.

## Commands

```
/root/proxmox-ops/pvectl.sh start    <id>            # power on
/root/proxmox-ops/pvectl.sh shutdown <id>            # graceful ACPI shutdown
/root/proxmox-ops/pvectl.sh stop     <id>            # hard stop
/root/proxmox-ops/pvectl.sh reboot   <id>
/root/proxmox-ops/pvectl.sh snapshot <id> [name]     # create (default auto-<timestamp>)
/root/proxmox-ops/pvectl.sh restore  <id> <snap>     # ROLLBACK to snapshot
/root/proxmox-ops/pvectl.sh delsnap  <id> <snap>     # delete a snapshot
/root/proxmox-ops/pvectl.sh backup   <id>            # vzdump backup
/root/proxmox-ops/pvectl.sh onboot   <id> on|off
```

## HARD RULES

1. **Two-step for every state change.** First run the command WITHOUT `--yes` to show the user
   the exact action + impact. Only after the user confirms, re-run the SAME command with `--yes`.
   Never add `--yes` on the first call.
2. **Snapshot before restore/destroy.** Before a `restore` (rollback) or anything that could lose
   state, take a `snapshot <id> pre-<what>` first so there's a way back.
3. **Respect impact.** `pvectl` prints the guest's role (e.g. "VM 101 runs YANGSuite :8480").
   If stopping/rebooting it causes user-visible downtime, say so and get explicit go-ahead.
4. **Diagnose first** with `pvectl status <id>` (or the `proxmox-triage` skill) before acting on
   an "unreachable" guest — it may simply be stopped.
5. **Never bypass the wrapper.** Raw `qm`/`pct` are intentionally not allowlisted. If `pvectl`
   can't do something, report that — don't reach around it.
6. **No command substitution in args** (`$(...)`, backticks) — keep `pvectl` arguments literal
   (avoids an OpenClaw exec-approval prompt and keeps the action auditable).

## Playbook: safe change to a running guest

```
pvectl status  <id>                 # confirm current state
pvectl snapshot <id> pre-change     # (no --yes) -> confirm -> re-run with --yes
# ... make the change ...
# if it goes wrong:
pvectl restore <id> pre-change      # (no --yes) -> confirm -> re-run with --yes
pvectl delsnap <id> pre-change --yes  # clean up once satisfied
```

## Known facts (host mairp)

- **VM 101 `cws-v1.1`** = Cisco YANGSuite on :8480, `onboot: 1`. Stopping it drops YANGSuite.
- **VM 100 `k3s-node`** normally stopped.
- PVE host firewall is disabled — not a factor in guest reachability.
