"""Authoring annotations travel with the validated component without new payload keys."""

from __future__ import annotations

import pytest

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.mermaid_authoring import MERMAID_AUTHORING
from clio_schemas.a2ui.validation import catalog_validators


def test_mermaid_annotation_is_on_the_component_and_does_not_change_payloads() -> None:
    catalog = render_workspace_catalog()
    component = catalog["components"]["clio.mermaid.v1"]
    assert component["x-clio-authoring"] == MERMAID_AUTHORING
    validator = catalog_validators(catalog)["clio.mermaid.v1"]
    source = {"id": "diagram", "component": "clio.mermaid.v1", "source": "flowchart LR\nA-->B"}
    validator.validate(source)
    validator.validate(
        {"id": "diagram", "component": "clio.mermaid.v1", "dataUri": "artifact://artifact_example"}
    )
    for invalid in (
        {**source, "dataUri": "artifact://artifact_example"},
        {**source, "x-clio-authoring": MERMAID_AUTHORING},
        {**source, "maxWidth": 800},
    ):
        assert not validator.is_valid(invalid)


@pytest.mark.parametrize("family", MERMAID_AUTHORING["families"], ids=lambda row: row["family"])
def test_each_recipe_is_an_ordinary_source_payload(family: dict[str, object]) -> None:
    """The whole inventory fits the actual contract, including its size constraints."""
    validator = catalog_validators(render_workspace_catalog())["clio.mermaid.v1"]
    validator.validate(
        {"id": "diagram", "component": "clio.mermaid.v1", "source": family["example"]}
    )
