# Tafsir GUI (NiceGUI)

User-friendly wrapper around the existing Tafsir pipeline. The GUI lives entirely under `tools/tafsir_gui` and **does not modify** any existing repository files.

## Quick start

1. Install the extra requirements (keep your existing environment):
   ```bash
   pip install -r tools/tafsir_gui/requirements.txt
   ```
2. Run the app:

   ```bash

   python -m tools.tafsir_gui.main
   ```

### TEST STRATEGY: ARCHITECTURE/CONTRACT + END-TO-END USER FLOWS

# Test Strategy

To ensure the quality of the new code, we will enforce the following contract tests and end-to-end user flow coverage tests.

#### ARCHITECTURE / CONTRACT TESTS (fast, deterministic, run on every change)

1. **UI Component API Compatibility Tests**
   - Create a test suite that instantiates every NiceGUI component used by the app and asserts required event hooks exist.
   - Example: for toggles/switches, do not assume `.on_change` exists; instead assert the supported hook method exists (e.g., `.on('update:model-value', ...)` or `.on_value_change(...)` depending on NiceGUI version) and fail fast if not.
   - Maintain a small compatibility shim in `ui/compat.py` with unit tests proving the shim routes events correctly for the installed NiceGUI version.

2. **Import/Module Integrity Tests**
   - Validate that `python -m tools.tafsir_gui.main` imports without side effects and without raising.
   - Validate that all new modules import cleanly (runner, preflight, gemini wrapper, scheduler, env, logging, pages).

3. **State Machine & Step Graph Tests**
   - Verify the step prerequisites and gating rules:
     - Start is disabled unless pre-flight is green
     - Preview confirmation gating (if enabled) blocks start
     - Mode switch invalidates preview, forces re-check
   - Assert allowed state transitions only (IDLE -> READY -> RUNNING -> PAUSED -> RUNNING -> COMPLETED / CANCELED / ERROR).

4. **Pre-flight Contract Tests**
   - Mock Gemini client and ensure:
     - valid key => green
     - invalid key => red with correct remediation message
     - rate-limit => yellow/red with RetryLater scheduled value
   - Mock file inputs for each supported type (PDF/CSV/SQLite/text) and assert sampling and type detection behave.

5. **Scheduler Contract Tests**
   - Ensure only one auto-resume job exists at a time.
   - Rescheduling replaces previous job and does not create duplicates.
   - RetryLater(seconds) schedules resume exactly once and runner ends in PAUSED.

6. **Artifact Versioning Tests**
   - Ensure schema/prompt/rules artifacts are written versioned.
   - Ensure switching prompt mode increments version and invalidates prior preview.

#### END-TO-END USER FLOW TESTS (broad coverage, can be slower)

Approach

- Use Playwright (Python) for browser-driven E2E tests of the NiceGUI app.
- Run the app in-process on a random free port for tests; open it via Playwright; click through flows; assert UI states, status badges, and logs.
- Mock network calls (Gemini) using dependency injection in the new code (integrations/gemini.py) so tests don’t call real APIs.

User Flows to Cover

1. Fresh start → complete pre-flight (mock OK) → preview OK → run pipeline (dummy step) → finalize
2. Invalid API key → immediate red status → Start remains disabled
3. Rate limited → “auto-resume” selected → scheduler queued → runner paused → resumed automatically (simulated)
4. File upload path invalid → pre-flight fails with remediation
5. Switch mode Legacy <-> Universal → preview invalidated → gating enforced
6. Custom prompt mode → preview rerun required → Start disabled until confirmed
7. Error during run (mock error) → UI shows error drawer with “next steps” → Cancel resets state
8. Open the shown local URL (defaults to `http://localhost:8080`).

## What it does

- Guides non-developers through the full pipeline via a 10-step wizard.
- Pre-flight validation before any long run (API key, cache, input file, output dir, SQLite access).
- Generates a Gemini cache on demand, samples the input to derive structure rules, and runs the existing `automate_gemini` pipeline.
- Live logs, status badges, pause/resume/cancel, and optional auto-resume when rate-limited.
- **Modes**: Legacy (tafsir-specific, calls existing modules) and Universal (AI-driven schema/rules/guards). Toggle on the left sidebar.
- Universal mode artifacts: `artifacts/schema_v*.json`, `validation_rules_v*.json`, `repair_policy_v*.json`, `guards_v*.json`, `prompt_v*.txt`, `validation_report.json`.
- Google Cloud Setup step: guided checklist, deep links, CLI/UI instructions, paste-and-test API key with live badge; pipeline stays disabled until the key validates in pre-flight.

## Folder layout (new files only)

```
tools/tafsir_gui/
  main.py                 # NiceGUI entrypoint
  requirements.txt        # GUI-only deps
  core/                   # runner, events, preflight, scheduler, state
  integrations/           # Gemini wrapper, adapters into existing pipeline
  ui/pages/               # wizard sections & run controls
  utils/                  # env, logging, file detection, db helpers
  storage/                # reserved for future metadata tables
  tests/                  # unit tests for new components
```

## Controls

- **Run pre-flight checks**: must be green before Start is enabled. Fails fast on key/cache/file/DB issues.
- **Start / Pause / Resume / Cancel**: orchestrate the pipeline without touching the underlying modules.
- **Logs panel**: tail of `tools/tafsir_gui/logs/gui.log` plus live runner events.

## Configuration

- Secrets are read from `.env` at launch. During Finalize, updated keys are written back via `python-dotenv`.
- Output projects default to `tools/tafsir_gui/projects/<project_name>/` with `source/` and `annotated/` subfolders.

## Tests

Run from repo root:

```bash
pytest tools/tafsir_gui/tests
```

### UI crawl smoke test

The crawler spins up the NiceGUI app through `tools.tafsir_gui.tests.e2e.app_runner`,
automatically clicks every button, watches for console errors, and confirms that the
themed helpers (cards, badges, layout classes, and the shared `theme.css`) render on the page.

```bash
pip install -r tools/tafsir_gui/tests/requirements.txt
playwright install
python -m tools.tafsir_gui.scripts.crawl_ui
```

You can pass `--scenario rate_limit`/`error`/`invalid_key` to exercise each mocked runner path or
`--no-headless` to watch the browser as it interacts with the UI.

## Notes

- The GUI uses the existing modules unchanged (`Tafsir.pipeline.gemini_api.blocks_to_xml_api.automate_gemini`, `Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline`, etc.). Paths are overridden in-memory so output stays under the project folder.
- PDF ingestion relies on `pypdf`; CSV/SQLite/text are handled with the standard library. If `pypdf` is missing, the PDF pre-flight check will fail with guidance.
