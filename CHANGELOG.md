# Changelog

## Unreleased

## [0.7.0b1] - 2026-11-11

### Added

- The `stream` artifact kind and the `clio-core` custody: an artifact whose content lives
  in clio-core as typed entries (its latest entry or a window), not as file bytes.
- A named artifact at its latest version, `artifact://<workspace>/<name>@latest`, as a
  live data source for charts, maps and tables.
- The `resource` message block: a workspace resource attached to a message, with
  how it was delivered to the agent (#6).
- The `context_reference` message block: a workspace file, artifact, session,
  agent run, evidence source, context frame, diff or plan the message points at.
- `metadata` on `notice` blocks: the answer hook that added the notice and the
  answer part its revision replaces.
- `metadata` on `injection` blocks: for a compaction's record, the messages it
  summarized and kept and the system prompt in force.

The message blocks describe what clio-agent already sends; `MessageBlock` now has 17
types.

## [0.6.0] - 2026-10-28

### Added

- Study-backed A2UI data sources and selection-bound viewer files.
- View-opening actions, workflow node actions and bindable selected nodes.
- Viewer height and initial table-page-size hints.

### Fixed

- Escape dotted column names in Vega-Lite preset fields.
- Resolve the selection named by an open-view action by its key.

This stable release includes the shared record and A2UI contracts from the
0.6.0 previews. The package and exported Python version both identify 0.6.0.
