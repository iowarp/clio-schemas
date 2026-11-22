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
| @apidevtools/json-schema-ref-parser | 11.9.3 | 16.0.8 | Transitive. json-schema-to-typescript 16.0.0 declares `^11.9.3`. Forcing it is a decision for you: see D1 below. |
| js-yaml / argparse under it | 4.3.2 / 2.0.1 | 5.5.0 / 3.0.4 | Same reason: `@apidevtools/json-schema-ref-parser` 11.9.3 declares `js-yaml: ^4.1.0`. |

Nothing was reverted: every major passed.

## Using what the upgrades offer

Beyond the version bumps, I looked for what the new versions let us do better.

### Adopted on this branch

Each was low-risk and is in its own commit, with the full gate passing. Committed schemas and
generated TS stay byte-identical.

| # | Change | Value | Why it is safe |
|---|---|---|---|
| A1 | **Pin every json-schema-to-typescript option** (`schemas-to-ts.mjs`). Adds `ignoreMinAndMaxItems: false`, `inferStringEnumKeysFromValues: false`, `maxItems: 20`, `unknownAny: true`, `unreachableDefinitions: false`. | The generator's comment already promised "fully-specified options so output does not depend on library defaults drifting", but these five still used the library's defaults. 16.0.0 already changed what `unreachableDefinitions` does, so a default is not a contract. | Each value is the current default (checked against `DEFAULT_OPTIONS`). Output byte-identical. |
| A2 | **Typecheck the generated TS with `verbatimModuleSyntax` and `erasableSyntaxOnly`** (`tsconfig.check.json`). | Consumers that compile one file at a time (Node's type stripping, esbuild, swc) need `export type` for type-only re-exports and can't handle enums or namespaces. Our output already meets both rules, but nothing enforced them. A generator option or upgrade that broke one would have passed `npm run check`. `erasableSyntaxOnly` needs TS >= 5.8, which the 7.0 upgrade gives us. | The current output passes. Negative controls (a `const enum`, a value-style `export { ArtifactRecord }`) are rejected (TS1294, TS1205). Output byte-identical. |
| A3 | **Metaschema test for every committed JSON Schema** (`tests/test_schemas_metaschema.py`). Runs jsonschema's `Draft202012Validator.check_schema` on the 27 per-model schemas, `index.json` and the clio-workspace `catalog.json`. | `export --verify` proves the committed bytes are what the locked pydantic renders, not that the render is a valid schema. 2.14 changed a lot of JSON Schema generation, and every future pydantic bump will too. The check includes format checks (e.g. `pattern` must compile as a regex) and fails if a file names a dialect other than 2020-12. | All 29 files pass today. Two negative controls show the check is live. Test only: +30 tests. |

Considered and not adopted (no value for us today):

- **pydantic 2.14's new features.** None touch our export path: `frozendict`, `TypeForm`, lazy imports, `EllipsisType`, `multiple_of` on `timedelta`/`Fraction`, `__namespace__` on `create_model`. The JSON Schema fixes in 2.14 (`Decimal` patterns, `InitVar`, `unless-none` serializers, deprecated subclasses, `str_min_length` config) don't hit our models: the regenerate is byte-identical. The one 2.14 feature that matters is the stable `MISSING` sentinel, which is a design call (D3).
- **TypeScript 7 itself.** Its value is speed. It needed no config change, and our `tsc` run is already sub-second, so nothing to adopt beyond A2.
- **Removing `flattenRefSiblings`** from `schemas-to-ts.mjs`. Under json-schema-to-typescript 16, the 8 `$ref`-with-sibling nodes in `index.json` no longer produce duplicate types: generating without the workaround is byte-identical. Removing it gains nothing and would bring back the old bug if a future generator regressed, so it stays. Its comment could note that 16 no longer needs it.
- **json-schema-to-typescript's upcoming `declarationStyle: 'type'` and `formatTypes`.** These are listed under "Next" in its changelog and are not in 16.0.0. `formatTypes` (e.g. `date-time -> Date`) would be wrong for us anyway: the wire carries strings.

### Decisions for the user

These are risky or design-level, so none is implemented. Each has the value, the risk and my
recommendation.

**D1. Force `@apidevtools/json-schema-ref-parser` 16 (held back at 11.9.3)**
- *Value:* low. It drops the second, older copy of js-yaml (4.3.2) and argparse (2.0.1), so js-yaml 5.5.0 is the only one installed. We don't resolve external or YAML `$ref`s: everything is internal `#/$defs`.
- *Risk:* json-schema-to-typescript 16.0.0 declares `^11.9.3`, so an npm `overrides` entry would run it on a resolver five majors newer, a combination nobody tested or supports. The resolver also needs Node >= 22.19.0, a tighter floor than the `node-version: "22"` our CI and gact-tui's `schema-ts-gen.yml` use today. I tried it in a throwaway copy: the generated TS was byte-identical.
- *Recommendation:* **hold.** Pick it up for free when json-schema-to-typescript widens its range.

**D2. Stop emitting a named type for every property `title` in the generated TS**
- *Value:* high for TS consumers. pydantic puts a `title` on every property, and json-schema-to-typescript turns each title into an exported alias. `_models.ts` therefore exports 577 names, 471 of them aliases like `export type Name = string`, and 240 have numeric suffixes from collisions (`Name1`, `Surfaceid1`, `Code1`, ...). Those names are noise in autocomplete, and they renumber whenever a model gains a same-titled field. Dropping property-level `title` in the TS-only transform (the same place `flattenRefSiblings` runs; the JSON Schema is untouched) gives 103 exports and 13 aliases. `_models.ts` goes from 1990 to 1515 lines, and the new output typechecks under the stricter A2 config. Model, enum and `$defs` names, and every per-model module, are unchanged.
- *Risk:* it's a breaking change to the TS API. Any consumer that imports one of the ~470 alias names (gact-tui, clio-agent) stops compiling. I couldn't check their code from this session. The golden changes almost entirely, and consumers' regenerate-and-compare CI goes red until they regenerate.
- *Recommendation:* **do it, but as its own coordinated change.** Grep gact-tui and clio-agent for imports of `_models` alias names first. Then ship it in one clio-schemas release with a CHANGELOG note, and land the regenerated TS in consumers right after. A middle option is `customName` to drop only the numbered aliases, but it still renames things, so a clean cut is better.

**D3. Use pydantic's now-stable `MISSING` sentinel for "absent" vs `null`**
- *Value:* 141 of the 520 properties in the aggregate are `X | None = None`. They export as `anyOf: [X, null]` with `"default": null`, and they dump as `null` when unset. With `x: X | MISSING = MISSING`, the field exports as plain `X` (not required, no default) and is left out of `model_dump()` when unset. That's a truer contract for "optional, never null" fields and tighter TS (`x?: X` instead of `x?: X | null`).
- *Risk:* it's a wire and schema change. Every converted field changes schema bytes (needs a version bump) and serialized output: writers stop sending `"x": null`. Readers that treat `null` and "missing" differently, or that send explicit `null`, break. The rollout rules in the README apply (readers before writers, adjacent versions interoperate). `MISSING` is also brand-new in stable pydantic.
- *Recommendation:* **don't convert existing fields wholesale.** Consider `MISSING` for new strict (`ClioSchemaBase`) records, field by field, where `null` has no meaning. Revisit existing fields only when a record is already getting a breaking change.

**D4. Put `$schema` in each per-model schema file**
- *Value:* the 27 per-model files don't declare a dialect. `index.json` and the catalog do. With `"$schema": "https://json-schema.org/draft/2020-12/schema"`, a consumer's validator (Ajv, jsonschema) picks 2020-12 instead of its default, which can be draft-07 (e.g. Ajv's default class). The A3 test would then check the declared dialect instead of assuming one.
- *Risk:* low technically (pydantic emits 2020-12), but it changes the bytes of all 27 shipped files and their hashes, so it needs a version bump, and consumers' byte checks see it. Some Ajv setups need the 2020 class to load a schema that declares 2020-12.
- *Recommendation:* **do it in the next schema-changing release**, so the byte churn rides along with a version bump that happens anyway. It's a small change in `render_model_schema`.

## Verification

Run after every group (each commit), on Python 3.13 with Node 22.23.5. The final dependency state
was also run on Python 3.12 (CI's version). The numbers below are for the final commit, which
includes A1-A3:

| Check | Result |
|---|---|
| `uv sync --extra dev --locked` | ok |
| `ruff check src tests scripts` | All checks passed |
| `ruff format --check src tests scripts` | 64 files already formatted |
| `pyright src tests scripts` | 0 errors (3.13 and 3.12) |
| `python -m clio_schemas.export --verify` | 44 committed schema files canonical |
| `scripts/check_version_bump.py --base v0.8.0` | ok (no schema bytes changed) |
| `uv build` | wheel + sdist build |
| `npm ci` + `pytest` (includes the TS round-trip/golden tests) | 984 passed: 954 before A3, also on 3.12; +30 from A3 |
| `npm run check` (generate + `tsc`, with A2's flags) | clean; output identical to `tests/golden` |

## Commits

1. Python patch/minor refresh
2. ts-gen patch/minor refresh, typescript 5.9.3
3. pydantic 2.14.4 (+ `LOCKED_PYDANTIC_VERSION`)
4. ruff 0.17.6
5. python-dateutil 4.0.0
6. json-schema-to-typescript 16.0.0 (+ regenerated golden)
7. typescript 7.0.2
8. this report
9. A1: pin every json-schema-to-typescript option
10. A2: `verbatimModuleSyntax` + `erasableSyntaxOnly` for the TS check
11. A3: metaschema test for the committed schemas
12. this report: adopted items and decisions
