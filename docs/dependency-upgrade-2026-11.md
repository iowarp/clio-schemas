# Dependency upgrade, 2026-11

Branch `chore/dependency-upgrade-2026-11`, from `main` at v0.8.0 (`9cd78e0`).

Outdated packages were listed with `uv tree --outdated` / `uv lock --upgrade --dry-run`
(Python) and `npm outdated --all` in `tools/ts-gen` (the only `package.json`).
After the upgrade both report nothing left to do except the two held-back transitive npm
packages below.

## Python (`pyproject.toml`, `uv.lock`)

No `pyproject.toml` constraint had to change: every new version is inside the existing
ranges. Only `uv.lock` moved (plus `LOCKED_PYDANTIC_VERSION`, see pydantic).

| Package | Kind | Current | Latest | Major? | Notes from the changelog that matter here |
|---|---|---|---|---|---|
| **pydantic** | direct | 2.13.4 | 2.14.4 | no (minor), but schema-generating | 2.14 has many JSON Schema generation changes: defaults are encoded with one consistent config, `Decimal` `pattern` was refactored and constraints no longer leak into it, `str_min_length`/`str_max_length` config now shows in the schema, `null` is added to serialization schemas for `unless-none` serializers, subclasses of `@deprecated` classes are no longer marked deprecated, single-alternative unions skip deduplication. Drops Python 3.9. JSON validation now looks fields up the same way Python validation does (2.14.2). **For us: `export --regenerate` under 2.14.4 rewrites all 44 committed schema files byte-identically**, so `HASHES.json` and the TS are unchanged and no version bump is needed. `LOCKED_PYDANTIC_VERSION` moved to 2.14.4. |
| pydantic-core | transitive | 2.46.4 | 2.50.5 | no | Moves with pydantic. |
| **jsonschema** | direct | 4.26.0 | 4.26.0 | — | Already current. |
| referencing | direct | 0.37.0 | 0.37.0 | — | Already current. |
| annotated-types | direct | 0.8.0 | 0.8.0 | — | Already current. |
| ruff | dev | 0.16.0 | 0.17.6 | yes (0.x minor = breaking) | 0.17 changes the default rule set (DTZ rules out, F406 in) and the default Python version (3.10 -> 3.11). Neither applies: we set `lint.select` and `target-version = "py312"`. JUnit output and ruff-lsp removal don't affect us. No code changes; `check` and `format --check` pass. |
| pytest | dev | 9.1.1 | 9.2.0 | no | `-c` with a bad path is now a usage error; higher-scoped fixtures as instance methods are deprecated; non-string values for string ini options warn. None used here. |
| pyright | dev | 1.1.411 | 1.1.414 | no | 0 errors before and after. |
| packaging | dev | 26.2 | 26.3 | no | — |
| python-dateutil | transitive (jsonschema[format] -> isoduration -> arrow) | 2.9.0.post0 | 4.0.0 | **yes** (2 -> 4) | 3.0 rewrote `tz.tzfile` and now depends on `tzdata`; 4.0 needs Python >= 3.11, drops `six` and makes `isoparse` strict about digit counts. Our code doesn't import it; the `duration`/`date-time` format checkers and arrow tz conversion were smoke-tested. `six` stays in the lock for rfc3339-validator. |
| fqdn | transitive | 1.5.1 | 1.6.0 | no | — |
| idna | transitive | 3.19 | 3.20 | no | — |
| iniconfig | transitive | 2.3.0 | 2.3.1 | no | — |
| jsonpointer | transitive | 3.1.1 | 3.12 | no | Version scheme jump only (3.1 -> 3.12). |
| nodeenv | transitive (pyright) | 1.10.0 | 1.12.0 | no | — |
| pluggy | transitive | 1.6.0 | 1.7.0 | no | — |
| pygments | transitive | 2.20.0 | 2.21.0 | no | — |
| rpds-py | transitive | 2026.6.3 | 2026.9.1 | no | — |
| typing-inspection | transitive | 0.4.2 | 0.4.5 | no | — |
| tzdata | transitive | 2026.4 | 2026.6 | no | — |

## TypeScript generation (`tools/ts-gen/package.json`, `package-lock.json`)

| Package | Kind | Current | Latest | Major? | Notes from the changelog that matter here |
|---|---|---|---|---|---|
| **json-schema-to-typescript** | direct (exact pin) | 15.0.4 | 16.0.0 | **yes** | 16.0.0 deliberately changes emitted types for some shapes: `oneOf`/`anyOf` + `properties`, `patternProperties` folding, `items` descriptions, `type: [object, null]` roots, empty `allOf` members, and others. It also moves to js-yaml 5 and prettier ^3.9 ("short unions that fit on one line are no longer wrapped"). **For us: only `tests/golden/_models.ts` changes, in three type-equivalent spots** (see below). |
| **typescript** | dev (exact pin) | 5.6.3 | 7.0.2 | **yes** (5 -> 7) | Done in two steps: 5.9.3 (latest 5.x) with the minor group, then 7.0.2. 7.0 is the native compiler; `tsc` now comes from a per-platform optional package (`@typescript/typescript-<os>-<cpu>`, all in the lockfile). 6.0/7.0 removed old options (`target: es5`, `moduleResolution: node10`/`classic`, `baseUrl`, ...); `tsconfig.check.json` uses none of them. Checked that 7.0 still rejects a deliberately broken file. |
| prettier | transitive | 3.9.6 | 3.10.1 | no | No change to our generated output. |
| js-yaml | transitive | 4.3.0 | 5.5.0 | yes | json-schema-to-typescript 16 now uses js-yaml 5 directly. A 4.3.2 copy stays for `@apidevtools/json-schema-ref-parser` (held back, below). |
| argparse | transitive | 2.0.1 | 3.0.4 | yes | Follows js-yaml (3.x under js-yaml 5, 2.x under js-yaml 4). |
| @types/lodash | transitive | 4.17.24 | 4.17.27 | no | — |
| picomatch | transitive | 4.0.5 | 4.0.7 | no | — |
| is-glob, is-extglob | transitive | 4.0.3, 2.1.1 | — | — | Removed by json-schema-to-typescript 16. |

### Generated TypeScript diff (json-schema-to-typescript 16)

Committed JSON Schemas are byte-identical across the whole upgrade. The generated TS is
byte-identical for every step except json-schema-to-typescript 16, where
`tests/golden/_models.ts` changes in three places and nothing else does:

```diff
-export type JsonValue = unknown | undefined;
+export type JsonValue = unknown;
```

```diff
 export interface Components {      // same change in Theme
   [k: string]:
-    | (
-        | {
-            [k: string]: unknown | undefined;
-          }
-        | boolean
-      )
+    | {
+        [k: string]: unknown | undefined;
+      }
+    | boolean
     | undefined;
 }
```

`unknown | undefined` is `unknown`, and the second is the same union with a redundant pair of
parentheses dropped. To confirm, old and new `JsonValue`, `Components`, `Theme` and
`InlineCatalog` were checked for mutual assignability under `tsc --strict`, with a negative
control that fails as it should. The golden was regenerated. Consumers that regenerate TS with
this generator (gact-tui's `schema-ts-gen.yml`) will see the same diff once when they move to
a commit that includes it.

## Held back

| Package | Current | Latest | Why |
|---|---|---|---|
| @apidevtools/json-schema-ref-parser | 11.9.3 | 16.0.8 | Transitive. json-schema-to-typescript 16.0.0 declares `^11.9.3`. Forcing 16.x with an `overrides` entry would run the generator on a resolver it was never released against, so we wait for json-schema-to-typescript to move. |
| js-yaml / argparse under it | 4.3.2 / 2.0.1 | 5.5.0 / 3.0.4 | Same reason: `@apidevtools/json-schema-ref-parser` 11.9.3 declares `js-yaml: ^4.1.0`. |

Nothing was reverted: every major passed.

## Verification

Run after every group (each commit), on Python 3.13 with Node 22.23.5, and at the end on
Python 3.12 (CI's version) too:

| Check | Result |
|---|---|
| `uv sync --extra dev --locked` | ok |
| `ruff check src tests scripts` | All checks passed |
| `ruff format --check src tests scripts` | 63 files already formatted |
| `pyright src tests scripts` | 0 errors (3.13 and 3.12) |
| `python -m clio_schemas.export --verify` | 44 committed schema files canonical |
| `scripts/check_version_bump.py --base v0.8.0` | ok (no schema bytes changed) |
| `uv build` | wheel + sdist build |
| `npm ci` + `pytest` (includes the TS round-trip/golden tests) | 954 passed (3.13 and 3.12) |
| `npm run check` (generate + `tsc`) | clean; output identical to `tests/golden` |

## Commits

1. Python patch/minor refresh
2. ts-gen patch/minor refresh, typescript 5.9.3
3. pydantic 2.14.4 (+ `LOCKED_PYDANTIC_VERSION`)
4. ruff 0.17.6
5. python-dateutil 4.0.0
6. json-schema-to-typescript 16.0.0 (+ regenerated golden)
7. typescript 7.0.2
8. this report
