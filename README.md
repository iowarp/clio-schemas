# clio-schemas

clio-schemas holds the data formats that the programs of the
[CLIO](https://iowarp.ai) system send to each other. Each format is written once
as a [pydantic](https://docs.pydantic.dev/) v2 model, and the package also ships
the [JSON Schema](https://json-schema.org/) generated from every model, so code
in any language can check a record or generate types from it.

Three programs read and write these records:
- [clio-agent](https://github.com/iowarp/clio-agent), the agent service;
- [gact-tui](https://github.com/iowarp/gact-tui), its desktop and web front end;
- [clio-relay](https://github.com/iowarp/clio-relay), which runs work on remote
  clusters.

Each program used to keep its own copy of shapes like "an artifact the agent
produced" or "a block of a chat message", and the copies slowly stopped
agreeing. Defining them here once, and checking every consumer against the same
bytes, is what keeps them in step.

The package is built for CLIO. The models are ordinary pydantic models and work
in any Python project, but which fields exist, how strictly they validate, and
how versions are released are all decided by what CLIO's services need. It is
not meant as a general-purpose schema library.

```bash
pip install clio-schemas==0.6.1   # pin an exact version; see "Versions" below
```

Python 3.12 or later.

## A worked example

`KnowledgeLink` records a link from one note to another, in a notes source such
as an Obsidian vault. It lives in `clio_schemas.knowledge`:

```python
class KnowledgeLink(ResourceContract):
    """An explicit link or embed; unresolved and ambiguous targets stay explicit."""

    source: str
    target: str
    selector: str = ""
    kind: Literal["link", "embed"] = "link"
    status: Literal["resolved", "unresolved", "ambiguous", "external"] = "resolved"
    candidates: list[str] = Field(default_factory=list)
```

The package ships the JSON Schema generated from it as
`clio_schemas/schemas/knowledge_link.json`:

<details>
<summary><code>knowledge_link.json</code></summary>

```json
{
  "additionalProperties": false,
  "description": "An explicit link or embed; unresolved and ambiguous targets stay explicit.",
  "properties": {
    "candidates": {
      "items": {
        "type": "string"
      },
      "title": "Candidates",
      "type": "array"
    },
    "kind": {
      "default": "link",
      "enum": [
        "link",
        "embed"
      ],
      "title": "Kind",
      "type": "string"
    },
    "selector": {
      "default": "",
      "title": "Selector",
      "type": "string"
    },
    "source": {
      "title": "Source",
      "type": "string"
    },
    "status": {
      "default": "resolved",
      "enum": [
        "resolved",
        "unresolved",
        "ambiguous",
        "external"
      ],
      "title": "Status",
      "type": "string"
    },
    "target": {
      "title": "Target",
      "type": "string"
    }
  },
  "required": [
    "source",
    "target"
  ],
  "title": "KnowledgeLink",
  "type": "object"
}
```

</details>

A Python consumer validates with the model; anything else can validate the same
record against the shipped schema:

```python
import json
from importlib.resources import files

import jsonschema
from clio_schemas.knowledge import KnowledgeLink

link = KnowledgeLink(source="notes/plan.md", target="notes/results.md")
schema = json.loads(files("clio_schemas").joinpath("schemas/knowledge_link.json").read_text())
jsonschema.validate(link.model_dump(mode="json"), schema)
```

Both reject a record that doesn't fit: `status="broken"` fails the model, and an
extra `"colour"` key fails the schema (`additionalProperties: false`).

TypeScript types are generated from the same JSON files by the script in
`tools/ts-gen`, not written by hand. For this model it produces:

```ts
export interface KnowledgeLink {
  candidates?: Candidates;
  kind?: Kind5;
  selector?: Selector;
  source: Source2;
  status?: Status;
  target: Target;
}
```

## What's in the package

| Module | Records |
|---|---|
| `models` | Artifacts the agent produces (`ArtifactVersion`, `ArtifactRecord`) and their provenance: how each was made (`TransformRecord`), what it used and produced (`ProvEdge`), the tool and environment involved (`Instrument`, `EnvironmentRecord`). |
| `gact_v3` | The 17 kinds of block a chat message is made of (text, reasoning, tool call, plan, task, subagent, artifact, attached resource, context reference, citation, diff, ...), as sent from clio-agent to its front ends. GACT is the protocol between them; these blocks are version 0.3. |
| `a2ui` | [A2UI](https://github.com/google/A2UI) 0.9.1, an open protocol for an agent to send user interfaces as data: the message and capability shapes, a vendored copy of the official spec, and CLIO's own catalog of 32 components with validators for it. |
| `knowledge`, `connected_resources` | Notes and links from knowledge sources such as Obsidian vaults, connected file sources, storage locations on a host, and a selection within a piece of content. |
| `model_capabilities`, `model_facts`, `model_parameters` | What a language model takes and produces, its description, release date, pricing and size, and the request settings it accepts. Every value names the source it came from; a value no source stated is left out or `null`. |
| `attention`, `attention_evidence` | Settings for the heat-map view of a model's attention over a transcript item, the reducer that recomputes a captured view, and the inspection record a reviewer rechecks against the session. |

`clio_schemas.export.EXPORTED_MODELS` lists every model that gets a JSON Schema
file.

## How the schemas stay identical everywhere

**The installed version fixes the exact schema bytes.** The JSON Schema files are
generated once, committed to this repository, and shipped inside the package;
consumers copy them rather than generating their own. That matters because two
pydantic releases can turn the same model into slightly different JSON Schema,
so a consumer that regenerated would drift without changing anything.

**Only one pydantic version may regenerate them.** `export --regenerate` refuses
to run unless the installed pydantic is the locked version
(`LOCKED_PYDANTIC_VERSION` in `constants.py`), so the committed files change only
when someone here changes them on purpose.

**Changing a schema requires a new version.** `HASHES.json` records a SHA-256 for
every shipped file. CI compares it with the last published release tag and
fails if a schema changed but the version did not.

**Consumers check their copies in CI.** clio-agent's CI exports the schemas from
the version it pins, byte-checks the copy, and runs its schema-equality tests
(`schema-check.yml`). gact-tui's CI regenerates its TypeScript and Zod types from
a pinned clio-schemas commit and fails if the result differs from what is
committed (`schema-ts-gen.yml`).

## Versions

Consumers pin an exact version (`clio-schemas==X.Y.Z`, never `>=`). With a range,
two services could resolve to different releases and disagree about a record.

- The version is set in two places that CI requires to match: `version` in
  `pyproject.toml` and `__version__` in `src/clio_schemas/__init__.py`.
- Any change to a shipped schema needs a version bump
  (`scripts/check_version_bump.py`).

Rolling out a change across services that briefly run different versions
follows three rules:

- **Readers before writers.** An addition (a new optional field, a new enum
  value) ships first to every service that reads the record, then to the ones
  that write it. Until then, readers must tolerate the new optional data.
- **Adjacent versions interoperate.** Services on version *N* and *N-1* must be
  able to exchange the records they share for the length of a rollout. A
  breaking change goes through at least one intermediate version, never all at
  once.
- **Roll back in reverse.** Retire the writers of a new shape before the readers
  that understand it, so a rolled-back writer never sends something a
  rolled-back reader would reject.

### Strict and tolerant records

New records inherit `ClioSchemaBase`: they reject unknown keys, don't coerce
types (no `"3"` for an `int`), and can't be modified after creation. The
artifact and provenance records in `models.py` were moved here from clio-agent
and keep clio-agent's original, more forgiving behavior through
`LegacyToleranceBase`: unknown keys are ignored and ordinary pydantic coercion
applies. Tightening them would change what the wire accepts, so it is planned as
a separate change coordinated with every consumer (iowarp/clio-agent#1121).

## The export command

```bash
# Copy the shipped schemas into ./schemas
uv run python -m clio_schemas.export --out schemas

# Check that ./schemas matches the shipped files exactly
# (fails on changed, missing, or extra files)
uv run python -m clio_schemas.export --out schemas --check

# Development only: regenerate the shipped files from the models
# (requires the locked pydantic version)
uv run python -m clio_schemas.export --regenerate

# This repository's CI: the committed files match the models and HASHES.json
uv run python -m clio_schemas.export --verify
```

## Development

```bash
uv sync --extra dev
uv run python -m clio_schemas.export --verify
uv run pytest

cd tools/ts-gen && npm ci && npm run check   # generate TypeScript and type-check it
```

`tests/golden/` holds the expected TypeScript output. `tests/test_roundtrip.py`
regenerates it and fails on any difference, which catches a change to a model,
a schema or the generator that nobody meant to make.

### Adding a model

1. Define the model, inheriting `ClioSchemaBase`, and give every field a
   `Field(description=...)`. Descriptions carry through to the JSON Schema and to
   the generated TypeScript comments.
2. Add it to `EXPORTED_MODELS` in `models.py`.
3. Regenerate the shipped schemas and the expected TypeScript:
   ```bash
   uv run python -m clio_schemas.export --regenerate   # schemas/ and HASHES.json
   cd tools/ts-gen && node schemas-to-ts.mjs \
       --in ../../src/clio_schemas/schemas --out ../../tests/golden
   ```
4. Bump the version in both places, then run `uv run pytest`.

### Repository layout

```
src/clio_schemas/
  models.py, gact_v3.py, knowledge.py, ...   the models (see the table above)
  export.py                                  copy / check / regenerate / verify
  constants.py                               LOCKED_PYDANTIC_VERSION, file names
  a2ui/                                      A2UI shapes, catalog rendering, validators
  schemas/                                   the committed JSON Schema files
    *.json, index.json                         one file per model, plus all of them
                                               in index.json with shared definitions
                                               emitted once
    HASHES.json                                SHA-256 of every shipped file
    a2ui/                                      the vendored A2UI spec and CLIO's
                                               rendered catalogs
tools/ts-gen/                                JSON Schema -> TypeScript generator
scripts/check_version_bump.py                CI: a schema change needs a version bump
tests/                                       includes golden/ (expected TypeScript)
ci-drafts/                                   early drafts of this repo's and the
                                             consumers' CI workflows
```
