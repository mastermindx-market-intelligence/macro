# Run the PB-D example on M2 Studio

## Where to run it

Open the **macOS Terminal application on the M2 Studio**. If you are viewing M2 Studio through a remote desktop session, open Terminal inside that session.

| Name | What it means for this task |
|---|---|
| M2 Studio | The computer with the prepared Python environment and Macro checkout |
| macOS Terminal app | The application in which to paste the command below |
| Macro repository | `mastermindx-market-intelligence/macro`; this contains the PB-D program |
| GitHub website | Stores the source, reviews and saved evidence; this example runs on M2 Studio |
| Mastermind / mastermind-terminal repositories | Separate projects; neither contains this PB-D launcher |

“Repository root” previously meant the local Macro folder containing `engine/`, `scripts/` and `tests/`. The command below supplies that location itself. You do not need to select a repository, change folders, activate Python, or install packages.

## Copy and paste this whole command

The prepared M2 Studio checkout is:

`/Volumes/Mastermind/agent-workspaces/macro/web/pb-d-operator-quickstart-20261008`

Paste this into **Terminal on M2 Studio** and press Return:

```bash
/bin/bash "/Volumes/Mastermind/agent-workspaces/macro/web/pb-d-operator-quickstart-20261008/scripts/run_pb_d_example.sh" \
  --output-dir "$HOME/Downloads"
```

This uses the checkout's own Python **3.12** environment. It does not use the machine's `python` alias, which selected Python 2.7 in the reported failed attempt.

The launcher creates a new folder inside your M2 Studio **Downloads** folder for each run. It saves the full JSON report there and prints its absolute location. Repeating the command is safe: earlier reports are retained.

## What successful output means

A successful run prints a short summary containing:

- that this is a **synthetic example**;
- study state `FROZEN_DESIGN_NOT_ENROLLED`;
- **1** complete synthetic pair;
- H5 difference **+4.0 percentage points**;
- all authority flags disabled;
- the absolute path of the newly saved report.

The values are read from the actual report. The launcher prints completion only after the existing research CLI succeeds and the report can be read.

The example is fictional. It checks that quality receipts, cohort freezing and evaluation connect correctly. It does not fetch current news or prices, open a website, enroll a real cohort, or produce evidence that the investment hypothesis works. The full research boundaries remain in [the implementation guide](PB_D_IMPLEMENTATION.md).

To inspect the report, open **Finder on M2 Studio**, select **Downloads**, and open the new `pb-d-example.*` folder. The report is JSON, so a text editor can display it. The Terminal summary already contains the useful demo result.

## Why the previous command failed

The reported path included:

```text
/Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python
```

That establishes that the bare `python` command selected Python 2.7. PB-D uses the tested Python 3.12 environment.

`No module named scripts` also means that interpreter could not locate Macro's `scripts` package. The earlier `python -m scripts...` example depended on starting inside the correct Macro checkout, which the instructions did not identify. The exact original working directory was not observed, so no stronger diagnosis of that directory is claimed.

The new launcher addresses both problems: it chooses an explicit interpreter and derives the Macro checkout from its own file location.

## Troubleshooting

| Message or symptom | Meaning and next step |
|---|---|
| The absolute launcher path does not exist | Confirm that Terminal is running on M2 Studio. This machine-specific path will not exist on another Mac or on the GitHub website. If the prepared checkout has been retired, use the operator checkpoint to prepare a current Macro environment before replacing this path. |
| The launcher's Python executable is missing | The prepared environment has been removed or the launcher belongs to a different checkout. The error prints the exact expected interpreter and this guide's location. Use the developer setup below for that checkout. |
| Python 3.12 is required | An explicit `--python` selection points to a different Python version. The prepared command above needs no override. |
| A dependency is missing | Install dependencies into the selected checkout's environment, using its exact Python executable. The launcher never installs packages automatically. |
| The output directory does not exist | `--output-dir` must name an existing folder. The verified M2 command uses your existing Downloads folder. |
| The underlying research command fails | Its diagnostic and nonzero exit status are preserved. A completion message is not printed; any already-created run folder is retained for inspection. |

## Developer use in another Macro checkout

This section is for a different checkout or machine. It is **not required for the prepared M2 command above**.

With Python 3.12 installed, open a terminal in that Macro checkout and create its isolated environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install numpy==2.3.5 PyYAML==6.0.3 jsonschema==4.26.0
/bin/bash scripts/run_pb_d_example.sh
```

The default environment is always the launcher's own checkout's `.venv/bin/python`. The launcher does not search other repositories or select `python` from `PATH`.

For an existing environment outside the checkout, use `--python` with its **absolute executable path**. The launcher validates that exact interpreter and does not fall back if it is unsuitable. `--output-dir` accepts an existing relative or absolute parent folder and always creates a fresh child folder. `--help` explains the arguments without running the example.

The machine-facing `quality`, `freeze`, `evaluate` and `run` interfaces remain unchanged. Their JSON schemas, scientific methods, overwrite refusal and authority boundaries are documented in [PB_D_IMPLEMENTATION.md](PB_D_IMPLEMENTATION.md).

## Evidence and continuity

Original implementation: [PR #8576](https://github.com/mastermindx-market-intelligence/macro/pull/8576), released as `9cb7173c4f08e1f6ca82281d886ee3637c1ed84a`.

Operator repair: `PB-D-OPERATOR-QUICKSTART-20261008`. The [cumulative checkpoint](PB_D_IMPLEMENTATION_CHECKPOINT.md) and `PB_D_OPERATOR_VERIFICATION.json` record the actual runtime, tests, source identities, publication and release receipt location.

The prepared M2 workspace is intentionally retained as the operator's runnable copy. Do not retire it while these instructions still direct the Chairman to it; update and verify the replacement path first.

**Standing delivery preference: save research to GitHub this turn and in future unless the Chairman redirects the destination.**
