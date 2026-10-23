# Ubuntu local inference capacity

This directory owns the **host-local admission boundary** for the paid-for RTX
5070 Ti on `mastermind-pc`. It does not own model selection, retries, queues,
worker lifecycle, or provider routing. Consumers keep using their existing
provider waterfalls.

## Runtime shape

- Ollama listens on loopback `127.0.0.1:11434`.
- Qwen `qwen3.5:9b` is the pinned local capacity model.
- `mastermind-inference.slice` caps inference at 4 CPU equivalents and 16 GiB
  RAM, with low CPU/I/O weight.
- `inference_guard.py` listens on loopback `127.0.0.1:11435` and admits one
  request only when host memory, the canonical CI cgroup, and GPU occupancy are
  safe.
- A refusal is HTTP 503. The caller's existing provider waterfall owns fallback.
- After each POST, the guard explicitly runs `ollama stop qwen3.5:9b` so the
  ~6.5 GiB model allocation does not remain resident and compete with other GPU
  work.

The 16 GiB host-MemAvailable floor is intentionally conservative on the current
62 GiB host: CI is independently capped at 12 GiB and inference at 16 GiB. It is
an admission hypothesis and may be changed only from measured host evidence.

## Installation

Ollama is installed from its official Linux distribution. Copy these reviewed
files onto the host:

```sh
sudo install -m 0644 mastermind-inference.slice /etc/systemd/system/mastermind-inference.slice
sudo install -m 0644 ollama-mastermind.conf /etc/systemd/system/ollama.service.d/mastermind.conf
sudo install -m 0755 inference_guard.py /usr/local/libexec/mastermind-inference-guard
sudo install -m 0644 mastermind-inference-guard.service /etc/systemd/system/mastermind-inference-guard.service
sudo systemctl daemon-reload
sudo systemctl enable --now ollama mastermind-inference-guard
```

Do not bind Ollama or the guard to a public/LAN address. Remote private callers
must use the already-owned authenticated host transport (for example a
tailnet-only TCP publication) and should still treat a 503 as normal fallback,
not as a reason to retry locally.

## Acceptance

1. `curl http://127.0.0.1:11435/healthz` reports `"ok": true` on an idle host.
2. A real earnings-harness request through `:11435/v1` returns a healthy Qwen
   row.
3. Immediately after response, `ollama ps` is empty and GPU model memory is
   released.
4. The existing CI services remain in `mastermind-ci.slice`; this change never
   moves or relabels a runner.
5. Under an injected guard test for low host memory, CI-memory-high, or another
   GPU compute workload, admission returns false without invoking Ollama.

Do not make a subscription-only GLM/MiniMax harness the unattended production
backend unless its canonical provider profile is separately admitted for
unattended production. Interactive fabric capacity and production daemon
authority are different contracts.
