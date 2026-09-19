"use strict";

// GitHub executes .js runner hooks with the runner's own absolute Node binary.
// Keep the policy in the adjacent root-owned Python file, but pass only the
// immutable GitHub facts and a profile derived from this root-owned filename.
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const profiles = {
  "mastermind-ci-admission-pc-ci.js": "pc-ci",
  "mastermind-ci-admission-pc-render.js": "pc-render",
  "runner_admission_m1_canary.js": "m1-canary",
};
const profile = profiles[path.basename(process.argv[1] || "")];
if (!profile) {
  console.error("::error title=runner-admission::unknown root-owned hook profile");
  process.exit(78);
}

const environment = {
  PATH: "/usr/bin:/bin",
  HOME: "/nonexistent",
  MASTERMIND_CI_PROFILE: profile,
};
for (const key of [
  "GITHUB_REPOSITORY",
  "GITHUB_EVENT_NAME",
  "GITHUB_REF",
  "GITHUB_WORKFLOW_REF",
  "GITHUB_JOB",
  "GITHUB_EVENT_PATH",
]) {
  environment[key] = process.env[key] || "";
}

const script = path.join(path.dirname(process.argv[1]), "runner_admission.py");
const result = spawnSync("/usr/bin/python3", ["-I", script], {
  env: environment,
  stdio: "inherit",
});
if (result.error || result.signal || !Number.isInteger(result.status)) {
  console.error("::error title=runner-admission::policy process failed closed");
  process.exit(78);
}
if (result.status !== 0) {
  process.exit(result.status);
}

// The production PC listener is a systemd --once service. Arm one ephemeral,
// root-owned reconciler only after trusted host admission. It carries no token,
// does not assign work, and stays inside the existing service cgroup. If GitHub
// has already made this exact bound job terminal while Runner.Listener remains
// alive, the helper signals that same listener and lets systemd's existing
// KillMode=control-group + Restart=always contract perform the recycle.
if (profile === "pc-ci" && (process.env.GITHUB_JOB || "") === "trusted-pack") {
  const runId = process.env.GITHUB_RUN_ID || "";
  const runAttempt = process.env.GITHUB_RUN_ATTEMPT || "";
  const runnerName = process.env.RUNNER_NAME || "";
  const runnerRoot = process.env.MASTERMIND_CI_RUNNER_ROOT || "";
  const validRoot = /^\/opt\/mastermind-ci\/runner-[1-4]$/.test(runnerRoot);
  if (/^[1-9][0-9]*$/.test(runId) &&
      /^[1-9][0-9]*$/.test(runAttempt) &&
      runnerName &&
      validRoot) {
    const watchdog = path.join(path.dirname(process.argv[1]), "runner_terminal_watchdog.py");
    try {
      const child = spawn(
        "/usr/bin/python3",
        [
          "-I",
          watchdog,
          "--repository", process.env.GITHUB_REPOSITORY || "",
          "--run-id", runId,
          "--run-attempt", runAttempt,
          "--runner-name", runnerName,
          "--ancestor-pid", String(process.ppid),
          "--runner-root", runnerRoot,
        ],
        {
          env: { PATH: "/usr/bin:/bin", HOME: "/nonexistent" },
          stdio: "ignore",
        },
      );
      child.on("error", () => {});
      child.unref();
    } catch (_error) {
      console.error("::warning title=runner-reconcile::terminal watchdog could not be armed");
    }
  } else {
    console.error("::warning title=runner-reconcile::terminal watchdog identity was incomplete");
  }
}
process.exit(0);
