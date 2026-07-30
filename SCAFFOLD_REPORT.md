# clio-schemas scaffold — build report (issue #1110, P0.6)

Pipeline-only bootstrap of the `iowarp/clio-schemas` package: a pydantic v2 ->
JSON Schema -> TypeScript loop, with the canonical schemas shipped as immutable
package resources, a golden anti-drift test, strict wire conformance, and CI
drafts for this repo and both consumers. This directory is intended to become
the real repo verbatim after review.

## CHANGES AFTER REVIEW (Codex verdict: no-ship — findings accepted)

Each accepted finding, the fix, and the proof it works.

1. **Design correction — immutable package resources, not consumer-side
   regeneration.** An exact pin does not fix schema *bytes* if consumers
   regenerate under their own pydantic.
   - *Fix:* canonical JSON Schemas are rendered once (under the locked pydantic)
     and committed as package resources in `src/clio_schemas/schemas/*.json`,
     shipped inside the wheel; a canonical `HASHES.json` (sha256) is committed
     alongside. `export.py` now has consumer modes that **copy** those bytes
     (`--out DIR`) or **verify** a copy (`--out DIR --check`), and dev/CI modes
     that render from the models (`--regenerate`, `--verify`) gated to
     `LOCKED_PYDANTIC_VERSION = 2.13.4`.
   - *Proof:* `uv run python -m clio_schemas.export --verify` → "OK: 4 committed
     schema file(s) are canonical"; wheel listing shows `clio_schemas/schemas/{schema_probe,probe_batch,index,HASHES}.json`
     + `py.typed`; `--regenerate`/`--verify` raise a clear error under any other
     pydantic (guard `_require_locked_pydantic`).

2. **Golden covers EVERY model + full-directory set equality.**
   - *Fix:* `test_golden_directory_set_and_bytes` compares the complete generated
     dir vs the complete golden dir (filename-set equality + byte content);
     `test_every_model_has_a_committed_schema` and
     `test_every_model_has_a_golden_ts_module` are parameterised over
     `EXPORTED_MODELS`.
   - *Proof:* 22 tests pass; `diff -rN tests/golden generated-ts` → "GOLDEN
     MATCHES FRESH GENERATION".

3. **Stale-artifact detection via clean temp dir + exact file SETS.**
   - *Fix:* the TS generator wipes its `--out` dir first (orphans cannot
     survive); the round-trip test generates into a fresh `tmp_path`; `export
     --check` rejects unexpected `.json` (`unexpected:` / `missing:` / `stale:`).
     The gact-tui CI draft now regenerates into a clean dir and uses `diff -rN`
     (not `git diff`, which misses untracked/orphans).
   - *Proof:* injecting `rogue.json` → `--check` exits 1 with "unexpected:
     rogue.json"; corrupting a file → exit 1 "stale: schema_probe.json".

4. **CI enforces version bump on schema change.**
   - *Fix:* `scripts/check_version_bump.py` compares `HASHES.json` against the
     merge base and fails if it changed without an `__version__` increment; pure
     core (`requires_bump`, `is_increment`) is unit-tested in
     `tests/test_version_bump.py`. Wired into `ci-drafts/clio-schemas-ci.yml`.
   - *Proof:* `check_version_bump.py` runs clean; 6 unit tests cover
     unchanged/changed/bumped/downgrade cases.

5. **Strict wire validation + negative conformance tests.**
   - *Fix:* `ClioSchemaBase(ConfigDict(extra="forbid", strict=True,
     frozen=True))`; both models inherit it. Tests assert `sequence="7"` (str
     for int) is rejected, unknown keys are rejected, and records are frozen.
   - *Proof:* `test_string_for_int_is_rejected`, `test_unknown_key_is_rejected`,
     `test_records_are_frozen` all pass.

6. **Multi-root readiness — shared definitions emitted once.**
   - *Fix:* second model `ProbeBatch` references `SchemaProbe` (nested) and reuses
     `ProbeKind` (shared enum). The exporter builds an aggregate `index.json` via
     pydantic `models_json_schema` (single shared `$defs`); the TS generator
     compiles that once into `_models.ts` (declarations), emits thin per-model
     re-export modules, and an `index.ts` barrel. A `$ref`-sibling flattening
     pass in the generator prevents json-schema-to-typescript from duplicating a
     ref'd type (it had produced `ProbeKind` + `ProbeKind1`).
   - *Proof:* declaration scan across `generated-ts` shows every type exactly
     once (`ProbeKind` count 1); `test_no_duplicate_declarations_in_barrel`
     passes.

7. **Packaging ships the schemas; documented consumption path.**
   - *Fix:* `[tool.hatch.build.targets.wheel].artifacts` force-includes
     `schemas/*.json` + `py.typed`; sdist includes `scripts`/`ci-drafts`. README
     documents that gact-tui copies the committed schemas from the installed
     package (pin ⇒ bytes) and runs the in-repo generator pinned by its lockfile.
   - *Proof:* wheel zip listing (see item 1) contains all four JSON files +
     `py.typed`; `uv build` produces wheel + sdist.

8. **README wire-evolution paragraph.**
   - *Fix:* added "Wire evolution" subsection: additive-reader-first staging,
     N/N-1 compatibility once real schemas land (P2.1 designs the full protocol),
     and rollback-in-reverse-of-deploy ordering. Exact-pin lockstep retained for
     the bootstrap.

## File inventory

| File | Purpose |
| --- | --- |
| `pyproject.toml` | hatchling build, `requires-python>=3.12`, `pydantic>=2.7,<3`; wheel force-includes `schemas/*.json` + `py.typed`; ruff/pytest/pyright config; `dev` extra. |
| `src/clio_schemas/__init__.py` | Public exports (models, `ClioSchemaBase`, `EXPORTED_MODELS`, `LOCKED_PYDANTIC_VERSION`) + `__version__`. |
| `src/clio_schemas/constants.py` | `LOCKED_PYDANTIC_VERSION`, aggregate/hash file names (import-cheap, avoids a `runpy` warning). |
| `src/clio_schemas/models.py` | `ClioSchemaBase` (strict/forbid/frozen), `ProbeKind` (shared enum), `SchemaProbe`, `ProbeBatch` (references SchemaProbe), `EXPORTED_MODELS`. |
| `src/clio_schemas/export.py` | Deterministic render + `copy` / `check` / `regenerate` / `verify` modes; aggregate schema; hash manifest; pydantic-lock guard; dir-diff (missing/unexpected/stale). |
| `src/clio_schemas/py.typed` | PEP 561 marker. |
| `src/clio_schemas/schemas/*.json` | **Committed immutable artifacts:** `schema_probe.json`, `probe_batch.json`, `index.json` (aggregate), `HASHES.json`. |
| `scripts/check_version_bump.py` | CI: schema-hash change ⇒ version-bump enforcement (pure, unit-tested core). |
| `tools/ts-gen/schemas-to-ts.mjs` | Aggregate -> `_models.ts` (once) + per-model re-export modules + `index.ts` barrel; `$ref`-sibling flattening; deterministic (fixed banner, sorted, LF). |
| `tools/ts-gen/package.json` + `package-lock.json` | Pins `json-schema-to-typescript@15.0.4` + `typescript@5.6.3`; `generate`/`check` scripts. |
| `tools/ts-gen/tsconfig.check.json` | Isolated strict typecheck (`types: []`, `lib: es2020`). |
| `tests/test_roundtrip.py` | Committed-canonical, per-model coverage, golden dir set+bytes, no-dup-declarations, strict conformance (negative) tests. |
| `tests/test_version_bump.py` | Unit tests for the version-bump core. |
| `tests/golden/*.ts` | Committed golden TS module graph (`_models.ts`, `index.ts`, `probe_batch.ts`, `schema_probe.ts`). |
| `ci-drafts/clio-schemas-ci.yml` | Own repo: ruff/pyright, `--verify`, version-pin agreement, version-bump script, golden round-trip, TS typecheck. |
| `ci-drafts/clio-agent-schema-check.yml` | Consumer: exact pin + `--out schemas --check` byte/set equality. |
| `ci-drafts/gact-tui-ts-gen.yml` | Consumer: copy shipped schemas, generate TS into clean dir, typecheck, `diff -rN` set+byte equality. |
| `README.md` | Purpose, immutable-resource design rationale, pipeline, export modes, add-a-model, exact-pin lockstep + wire-evolution, consumer regeneration. |
| `.gitignore` | Ignores venv/caches/dist/node_modules/`generated-ts`/`.ts-fresh`/top-level `schemas/`; keeps `src/clio_schemas/schemas/` tracked. |
| `uv.lock` | Resolved lock (pins pydantic 2.13.4 = LOCKED_PYDANTIC_VERSION). |

## Verify locally

```bash
cd clio-schemas-scaffold

uv sync --extra dev
uv run python -m clio_schemas.export --verify            # committed artifacts canonical
uv run python -m clio_schemas.export --out /tmp/s        # consumer copy
uv run python -m clio_schemas.export --out /tmp/s --check  # exit 0 = matches
uv run --extra dev ruff check src tests scripts
uv run --extra dev ruff format --check src tests scripts
uv run --extra dev pyright src tests scripts
uv run --extra dev pytest                                # 22 passed
uv run python scripts/check_version_bump.py --base origin/main
uv build                                                 # wheel + sdist (schemas inside)

cd tools/ts-gen && npm ci && npm run check               # generate TS + strict typecheck
```

## Verified in this session (all green)

- `--verify`: 4 committed schema files canonical (match models + HASHES under
  locked pydantic 2.13.4).
- `pytest`: **22 passed** — committed-canonical, per-model coverage (×2), golden
  dir set+bytes, no-duplicate-declarations, negative conformance (str-for-int,
  unknown-key, frozen), version-bump unit tests.
- Consumer copy + `--check` pass; injected unexpected file and corrupted file
  each fail `--check` with a typed reason.
- `ruff check` + `ruff format --check` + `pyright` (src/tests/scripts) clean.
- TS generation: `_models.ts` declares every type exactly once (`ProbeKind`
  shared enum once); per-model re-export modules + barrel; strict `tsc` passes;
  `diff -rN tests/golden generated-ts` identical.
- `uv build`: wheel + sdist; wheel contains `schemas/*.json` + `py.typed`.
- `check_version_bump.py` runs clean.

## Not verified / caveats

- **CI YAML files are drafts, not executed** in a real Actions runner. Step
  logic mirrors commands verified locally, but action versions
  (`astral-sh/setup-uv@v5`, `actions/setup-node@v4`) and consumer-repo paths
  (e.g. gact-tui `src/generated/schemas`) must be reconciled on adoption.
- **Consumer snippets assume a published/installable `clio-schemas==0.1.0`.**
  Until the repo is published (PyPI or git pin), `uv pip install
  "clio-schemas==0.1.0"` / dependency-pin steps will not resolve. Locally it
  installs from source (`uv sync`, `uv build`).
- **`LOCKED_PYDANTIC_VERSION` is hardcoded to 2.13.4** (matching `uv.lock`).
  Bumping pydantic is a deliberate action: update the constant, `--regenerate`,
  and version-bump. `--verify`/`--regenerate` correctly refuse under any other
  installed pydantic — this is by design, not a bug.
- **`json-schema-to-typescript` determinism is pinned by version** (15.0.4), not
  proven across versions; the golden guards it and a bump requires regenerating
  the golden.
- **`check_version_bump.py` merge-base logic** is exercised only via its pure
  unit-tested core here (the scaffold dir is not a git repo with an `origin/main`
  history); in a real repo it diffs against the base ref.
- Windows note: the generator normalises CRLF->LF; verified on win32.
