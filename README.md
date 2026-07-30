# clio-schemas

**The single source of truth for the record shapes shared across the CLIO
system.** `clio-agent`, `clio-relay`, and `gact-tui` all speak the same wire
records — `TaskRecord`, `ArtifactRef`, `ArtifactUse`, and the part-record
shapes. Historically each service hand-wrote its own copy of these types and
they drifted. This package makes the shapes canonical: they are defined once as
[pydantic](https://docs.pydantic.dev/) v2 models here and exported to JSON
Schema. Python consumers import the models; TypeScript consumers **generate**
types from the JSON Schema shipped inside the package. Nobody hand-writes a
shared shape again.

> **Status: bootstrap (P0.6 / issue #1110).** Only the *pipeline* exists right
> now, proven end to end by two placeholder models (`SchemaProbe` and
> `ProbeBatch`, which references it and shares an enum). The real record content
> lands in slice **P2.1 (#1120)**. Do not depend on the placeholders — they are
> deleted when the real models arrive.

---

## Why the schemas are immutable package resources (design decision)

An exact `clio-schemas` pin, on its own, does **not** guarantee two services see
the same schema *bytes*: if each consumer *regenerated* JSON Schema from the
pydantic models under its own resolved pydantic version, a pydantic point release
could subtly change the output and drift would return through the back door.

So the canonical JSON Schemas are **built once, committed, and shipped as
immutable package resources** inside the wheel (`clio_schemas/schemas/*.json`),
alongside a canonical hash manifest (`HASHES.json`). Consumers **copy** those
committed bytes — they never regenerate. An exact pin therefore *does* determine
the bytes. Regenerating from the models is a repo-local developer command
(`--regenerate`), gated to the single **locked pydantic version**, so the
committed artifacts can only change deliberately, in this repo.

## What's in the box

```
clio-schemas/
├── pyproject.toml                     # uv-compatible, py>=3.12, pydantic v2, hatchling
├── src/clio_schemas/
│   ├── __init__.py                    # public exports + __version__
│   ├── constants.py                   # LOCKED_PYDANTIC_VERSION, file names
│   ├── models.py                      # canonical models + ClioSchemaBase + registry
│   ├── export.py                      # copy / check / regenerate / verify
│   ├── py.typed                       # ships type information
│   └── schemas/                       # COMMITTED immutable artifacts (in the wheel)
│       ├── schema_probe.json          #   per-model, self-contained
│       ├── probe_batch.json           #   per-model, self-contained
│       ├── index.json                 #   aggregate: shared $defs emitted once
│       └── HASHES.json                #   canonical sha256 manifest
├── tools/ts-gen/
│   ├── schemas-to-ts.mjs              # JSON Schema dir -> TS module graph (deterministic)
│   ├── tsconfig.check.json            # isolated strict typecheck of generated TS
│   └── package.json / package-lock.json
├── scripts/check_version_bump.py      # CI: schema change ⇒ version bump
├── tests/
│   ├── test_roundtrip.py              # golden anti-drift + conformance tests
│   ├── test_version_bump.py           # unit tests for the bump-enforcement core
│   └── golden/                        # committed golden TS directory
│       ├── _models.ts index.ts probe_batch.ts schema_probe.ts
└── ci-drafts/                         # workflow drafts for this repo + both consumers
```

## The pipeline

```
pydantic models ──render (locked pydantic)──▶ committed *.json + HASHES.json ──ship in wheel──▶
    consumer copies bytes ──schemas-to-ts.mjs──▶ TypeScript module graph
```

Every hop is **deterministic**: JSON is emitted with sorted keys and a stable
`$defs` order; the TypeScript generator uses a fixed banner (no timestamp),
sorted file order, and pinned formatting. The aggregate `index.json` carries all
models under a single shared `$defs`, so the generator emits each shared
definition (e.g. the `ProbeKind` enum, the nested `SchemaProbe`) **exactly
once** — the generated module graph has no duplicate declarations.

## Export command modes

```bash
# Consumer: copy the immutable committed schemas into ./schemas
uv run python -m clio_schemas.export --out schemas

# Consumer CI: verify a directory matches the committed bytes exactly
# (rejects stale, missing, AND unexpected/orphaned files)
uv run python -m clio_schemas.export --out schemas --check

# DEV: re-render the committed package resources from the models
# (refuses unless the installed pydantic == LOCKED_PYDANTIC_VERSION)
uv run python -m clio_schemas.export --regenerate

# REPO CI: assert committed artifacts are canonical (match models + hashes)
uv run python -m clio_schemas.export --verify
```

## Quick start

```bash
uv sync --extra dev                                   # install (locked pydantic)
uv run python -m clio_schemas.export --verify         # artifacts are canonical
uv run pytest                                          # golden round-trip + conformance

cd tools/ts-gen && npm ci && npm run check            # generate TS + strict typecheck
```

## How to add a model

1. Define the pydantic v2 model in `src/clio_schemas/models.py`, inheriting
   `ClioSchemaBase` (strict wire semantics: `extra="forbid"`, `strict=True`,
   `frozen=True`). Give every field a `Field(description=...)` — descriptions flow
   into the JSON Schema and the generated TS doc comments.
2. Append the class to the `EXPORTED_MODELS` tuple in the same file.
3. Regenerate the committed artifacts and the golden TS, then bump the version:
   ```bash
   uv run python -m clio_schemas.export --regenerate            # updates schemas/ + HASHES.json
   cd tools/ts-gen && node schemas-to-ts.mjs \
       --in ../../src/clio_schemas/schemas --out ../../tests/golden
   ```
4. Bump `__version__` in `src/clio_schemas/__init__.py` **and** `version` in
   `pyproject.toml` in lockstep (CI enforces a bump whenever `HASHES.json`
   changes), then `uv run pytest`.

## Versioning policy — exact-pin lockstep

Consumers pin an **exact** version (`clio-schemas==X.Y.Z`, not `>=`). A schema is
a contract between multiple services; a range would let two services resolve
different shapes and reintroduce drift. Therefore:

- **Any** change to a committed schema (detected via `HASHES.json`) requires a
  `clio-schemas` version bump — enforced mechanically in CI by
  `scripts/check_version_bump.py`, which compares the hash manifest against the
  merge base and fails if the version was not incremented.
- All consumers (`clio-agent`, `clio-relay`, `gact-tui`) update their pin to the
  new exact version **in lockstep**, in the same coordinated change.
- The version lives in exactly two places that must agree: `pyproject.toml`
  `version` and `clio_schemas.__version__`; CI verifies they match.

### Wire evolution (forward-looking; full protocol designed in P2.1)

Exact-pin lockstep is the bootstrap rule. As the real records land and the
system runs mixed versions during rollouts, the intended evolution discipline
is:

- **Additive, reader-first staging.** Additive changes (new optional field, new
  enum member) ship to *readers* before *writers*: deploy the version that can
  *accept* the new shape everywhere first, then deploy the writers that *emit*
  it. Readers must ignore-or-tolerate unknown-but-optional additions during the
  transition. (Note: today's `extra="forbid"` is deliberately strict for the
  bootstrap; P2.1 defines exactly which surfaces relax to reader-tolerant.)
- **N / N-1 compatibility.** Once real schemas exist, adjacent versions are
  expected to interoperate: a service on version *N* and one on *N-1* must be
  able to exchange the records they share for the duration of a rollout.
  Breaking (non-additive) changes require a two-step migration across at least
  one intermediate version, never a flag-day.
- **Rollback ordering.** Roll back in the reverse of deploy order: retire the
  *writers* of a new shape before the *readers* that understand it, so a rolled
  -back writer never emits a shape an already-rolled-back reader would reject.

P2.1 (#1120) designs the full protocol (compatibility classes, the deprecation
window, and the migration tooling); this section records the intended direction
so the bootstrap does not bake in an incompatible assumption.

## How consumers regenerate

- **clio-agent (Python):** pin `clio-schemas==X.Y.Z`, `import clio_schemas`. Its
  CI copies the committed schemas out of the installed package and `--check`s any
  vendored copy for exact-byte + file-set equality (see
  `ci-drafts/clio-agent-schema-check.yml`).
- **clio-relay (Python):** same as clio-agent — import the models, pin exact.
- **gact-tui (TypeScript):** pin `clio-schemas==X.Y.Z`, copy the shipped JSON
  Schema out of the package, and run the in-repo generator (`tools/ts-gen`,
  pinned via its lockfile) to produce `.ts`. Its CI regenerates into a clean dir
  and compares exact file *sets* + bytes so untracked/orphaned files are caught
  (see `ci-drafts/gact-tui-ts-gen.yml`).
```
