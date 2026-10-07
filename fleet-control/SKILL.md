---
name: fleet-control
description: >
  Operate the mairp fleet control plane and read its health: bring the LLM/observability
  stack up or down (fleet.sh), check the RTX 3090 eGPU (gpu status / safe power off / power up),
  and get an observability digest. Use when asked to "start/stop/restart the fleet",
  "fleet status", "GPU status", "power the GPU down/up", or "how's the stack doing".
---

# Fleet control & health

Thin wrapper over the host's existing, proven ops scripts on **mairp**. Prefer these over
ad-hoc `docker`/`systemctl`. No new logic — read the script output and relay it.

## Fleet stack (LiteLLM + llama-swap + observability + duby + qmd gateway)

```
/root/fleet.sh status        # health of every component + ports (read-only)
/root/fleet.sh start         # bring the stack up in dependency order
/root/fleet.sh restart       # stop then start
/root/fleet.sh stop          # stop (leaves shared LLM core up; add --all to include it)
```

## RTX 3090 eGPU (Thunderbolt-4 enclosure)

```
/root/gpu_rtx_3090/gpu-status.sh                 # util/VRAM/temp/power/PCIe link (read-only)
/root/gpu_rtx_3090/gpu-safe-shutdown.sh --detach # drain GPU + PCIe hot-remove (before power-off)
/root/gpu_rtx_3090/gpu-power-up.sh --serve       # re-enumerate PCIe + start llama-swap
```

## Observability digest

```
/root/agent-observability-stack/onboard/observ-digest.sh   # runs onboarding + prints health digest
```

## HARD RULES

- `status`/`gpu-status.sh`/`observ-digest.sh` are read-only — safe to run any time.
- `fleet.sh start|stop|restart` and the GPU power scripts CHANGE state. Confirm with the user
  before stopping/restarting the fleet or powering the GPU down — agents and inference depend on it.
- Do NOT use web_fetch against localhost (blocked for private IPs); these scripts use curl internally.
- Keep output concise. No emojis.

## Notes

- `fleet.sh` brings up: LiteLLM (:4000) + llama-swap (:8081) → observability (:3000) → duby →
  **qmd gateway (:8190)**. The OpenClaw gateway (:18789) autostarts as a user service (reported only).
- Powering the GPU down stops local qwen inference (llama-swap); Compass/gpt-5 via the shim still work.
