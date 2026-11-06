# Ubuntu local inference capacity

This directory owns the **host-local admission boundary** for the paid-for RTX
5070 Ti on `mastermind-pc`. Consumers retain their existing provider waterfall,
model selection, fallback and worker lifecycle. This guard admits only the
already-pinned local capacity model; it does not add a scheduler, queue or retry
owner.

## Runtime contract

- Ollama remains on `127.0.0.1:11434`; the guard remains on `127.0.0.1:11435`.
  The executable rejects non-loopback addresses, identical listen/upstream
  endpoints and a model other than `qwen3.5:9b` before creating a server.
- One operation may hold the admission slot. Contending requests receive HTTP
  503 before any request body or telemetry is read. At most four connection
  handlers exist; excess connections are refused instead of queued in Python.
- The supported consumer paths are `GET /healthz`, `GET /v1/models` and
  non-streaming `POST /v1/chat/completions` for the pinned model. Management,
  alternate model and streaming requests are rejected without inference.
- Requests and upstream responses are capped at 8 MiB. Body reads have a
  five-second deadline, as do request headers. Upstream operations have a
  90-second deadline that interrupts the socket even for dripping headers;
  socket timeouts and bounded response reads also apply. This leaves room for
  admission and cleanup within the known earnings client's 120-second response
  timeout. Oversized, ambiguous, incomplete or malformed input is rejected.
- Admission requires the existing 16 GiB host-MemAvailable floor, a valid
  canonical CI cgroup below `memory.high`, and at most 512 MiB of GPU compute
  occupancy. All compute processes count, including processes named Ollama or
  llama-server. Missing, malformed, negative or unavailable telemetry refuses
  admission rather than becoming an idle-host reading.
- A bounded `GET /api/ps` on the existing upstream must also show no resident
  model. This check runs on each admission, including health checks; an old
  model left by a failed cleanup is not silently accepted on the next request.
- After an attempted inference, the guard performs one `ollama stop
  qwen3.5:9b` against the same validated loopback upstream, overriding any
  inherited `OLLAMA_HOST`, and verifies empty model residency **before**
  releasing a response.
  A failed stop or unverified residency returns 502 instead of the buffered
  result. There is no cleanup retry loop. The caller still owns fallback, and
  existing host operators own any repair of persistent residency failures.
- Both guard and Ollama belong to the existing `mastermind-inference.slice`:
  four CPU equivalents, 12 GiB high / 16 GiB hard RAM limits, 2 GiB swap limit
  and low CPU/I/O weight. The original slice and Ollama drop-in stay unchanged.

The memory floor is an admission hypothesis for the historically measured
62 GiB host, where CI is independently capped at 12 GiB. Changing those limits
requires current measured host evidence. This source repair changes none of
them. The pinned upstream may advertise other installed models through its
inventory endpoint; this guard still refuses inference for any other model.

## Installation

Ollama is installed from its official Linux distribution. The following are
operator installation instructions, not evidence of an installation performed
by the source repair:

```sh
sudo install -m 0644 mastermind-inference.slice /etc/systemd/system/mastermind-inference.slice
sudo install -m 0644 ollama-mastermind.conf /etc/systemd/system/ollama.service.d/mastermind.conf
sudo install -m 0755 inference_guard.py /usr/local/libexec/mastermind-inference-guard
sudo install -m 0644 mastermind-inference-guard.service /etc/systemd/system/mastermind-inference-guard.service
sudo systemctl daemon-reload
sudo systemctl enable --now ollama mastermind-inference-guard
```

Remote private consumers must use their already-owned authenticated host
transport. A refusal is an ordinary signal to their existing fallback; it is
not a request to retry locally or publish a new public/LAN listener.

## Qualification and deployment acceptance

The focused source suite simulates host telemetry, HTTP bodies/responses and
the unload process. It checks contention, bounded input/output, malformed GPU
readings, resident-model refusals, cleanup failures, allowed consumer paths and
the unchanged resource envelope. It never invokes real nvidia-smi, Ollama,
systemd, credentials, providers or the earnings worker.

Historical real-host canaries apply to their historical code only. Fresh
deployment acceptance of this amended guard still requires the incumbent host
owner to show:

1. Idle-host `/healthz` succeeds and a real earnings request through `:11435/v1`
   returns a healthy pinned-model result.
2. Immediately afterward, model residency is empty and GPU allocation is
   released; an injected cleanup failure cannot produce a successful response.
3. Busy, low-memory, CI-high and invalid-telemetry conditions refuse admission
   while the existing caller waterfall remains functional.
4. CI services remain in `mastermind-ci.slice`; no runner is moved or relabelled.

Source landing does not admit a production provider route, a Fabric Worker or
a new daemon deployment. Subscription-only harnesses still require their
separate canonical provider admission before unattended production use.
