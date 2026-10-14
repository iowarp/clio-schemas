"""Carousel composition and existing video playback agree across both validators."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from clio_schemas.a2ui.catalog_export import render_workspace_catalog
from clio_schemas.a2ui.v0_9_1.components import CarouselComponent, VideoComponent
from clio_schemas.a2ui.validation import catalog_validators


@pytest.mark.parametrize("active", [None, "second", {"path": "/guide/slide"}])
def test_carousel_accepts_child_references_and_optional_navigation(active: Any) -> None:
    payload = {"id": "root", "component": "Carousel", "children": ["first", "second"]}
    if active is not None:
        payload["activeChild"] = active
    CarouselComponent.model_validate(payload)
    catalog_validators(render_workspace_catalog())["Carousel"].validate(payload)


@pytest.mark.parametrize("children", [[], "image", [1], [{"id": "image"}]])
def test_carousel_rejects_empty_or_nested_content(children: Any) -> None:
    payload = {"id": "root", "component": "Carousel", "children": children}
    with pytest.raises(ValidationError):
        CarouselComponent.model_validate(payload)
    assert not catalog_validators(render_workspace_catalog())["Carousel"].is_valid(payload)


@pytest.mark.parametrize("url", ["artifact://artifact_clip", {"path": "/clip"}])
def test_workspace_video_uses_the_existing_media_url_contract(url: Any) -> None:
    payload = {"id": "clip", "component": "Video", "url": url}
    VideoComponent.model_validate(payload)
    catalog_validators(render_workspace_catalog())["Video"].validate(payload)


def test_layout_does_not_duplicate_image_or_video_source_properties() -> None:
    """Slides compose ordinary reference-backed components rather than inline media bytes."""
    properties = render_workspace_catalog()["components"]["Carousel"]["allOf"][-1]["properties"]
    assert set(properties) == {"component", "children", "activeChild"}
