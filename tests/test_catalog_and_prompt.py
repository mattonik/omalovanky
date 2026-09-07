import pytest
from pydantic import ValidationError

from app.catalog import CHARACTER_BY_ID, catalog_payload
from app.prompting import build_color_preview_prompt, build_image_prompt
from app.schemas import GenerationRequest


def test_catalog_contains_requested_cars_characters() -> None:
    assert CHARACTER_BY_ID["lightning-mcqueen"].label == "Bleskový McQueen"
    assert CHARACTER_BY_ID["mater"].label == "Mater / Burák"
    assert {
        "lightning-mcqueen",
        "mater",
        "sally",
        "cruz-ramirez",
        "jackson-storm",
        "mack",
    }.issubset(CHARACTER_BY_ID)
    assert CHARACTER_BY_ID["rumi"].label == "Rumi"
    assert CHARACTER_BY_ID["huntrix"].label == "HUNTR/X"
    assert len(catalog_payload()["characters"]) == 19


def test_catalog_groups_characters_and_exposes_optional_scenes() -> None:
    payload = catalog_payload()

    assert [theme["label"] for theme in payload["character_themes"]] == [
        "Rozprávky",
        "Labková patrola",
        "Autá",
        "Demon Hunters",
    ]
    assert {scene["id"] for scene in payload["scenes"]} >= {"castle", "city", "forest"}


def test_princess_on_unicorn_prompt_is_simple_and_printable() -> None:
    request = GenerationRequest(
        worlds=["princesses", "unicorns"],
        characters=["princess", "unicorn"],
        action="riding",
        custom_idea="princezná jazdí na jednorožcovi cez dúhový most",
        orientation="portrait",
    )

    prompt = build_image_prompt(request)

    assert "original cheerful fairy-tale child character" in prompt
    assert "original friendly magical unicorn" in prompt
    assert "dúhový most" in prompt
    assert "thick, smooth, consistent outlines" in prompt
    assert "no color, gray, shading" in prompt
    assert "no text, letters, numbers" in prompt


def test_three_pups_and_mighty_variant_are_supported() -> None:
    request = GenerationRequest(
        worlds=["rescue-pups"],
        characters=["zuma", "rocky", "skye", "mighty-pups"],
        action="rescuing",
        orientation="landscape",
    )

    prompt = build_image_prompt(request)

    assert "original orange rescue puppy" in prompt
    assert "original green recycling puppy" in prompt
    assert "original pink flying puppy" in prompt
    assert "bright superhero variant" in prompt
    assert "left to right" in prompt


def test_cars_prompt_uses_generic_original_descriptions() -> None:
    request = GenerationRequest(
        worlds=["cars"],
        characters=["lightning-mcqueen", "mater"],
        action="racing",
        orientation="landscape",
    )

    prompt = build_image_prompt(request)

    assert "original bright red cartoon race car" in prompt
    assert "original friendly rusty tow truck" in prompt
    assert "signature silhouette" in prompt


def test_prompt_avoids_brand_names() -> None:
    request = GenerationRequest(
        worlds=["kpop-demon-hunters"],
        characters=["rumi", "mira", "zoey", "huntrix"],
        action="rescuing",
        orientation="portrait",
    )

    prompt = build_image_prompt(request)

    assert "original pop-star adventure world" in prompt
    assert "original confident young pop singer" in prompt
    assert not any(name in prompt for name in ("PAW Patrol", "Lightning McQueen", "K-pop Demon Hunters", "Disney", "Pixar"))


def test_character_selection_derives_its_theme() -> None:
    request = GenerationRequest(
        characters=["unicorn"],
        action="riding",
    )

    prompt = build_image_prompt(request)

    assert request.worlds == ["unicorns"]
    assert "magical unicorn" in prompt
    assert "original magical-animal world" in prompt
    assert "Worlds: an original fairy-tale world" not in prompt


def test_generation_defaults_to_landscape_without_background() -> None:
    request = GenerationRequest(characters=["mater"], action="racing")
    prompt = build_image_prompt(request)

    assert request.orientation == "landscape"
    assert "Background: no specific background scene." in prompt
    assert "Do not add princesses, castles" in prompt


def test_color_preview_prompt_requests_full_color_reference() -> None:
    request = GenerationRequest(
        worlds=["cars"],
        characters=["lightning-mcqueen", "mater"],
        action="racing",
        orientation="landscape",
        generation_mode="color_first",
    )

    prompt = build_color_preview_prompt(request)

    assert "full-color children's reference illustration" in prompt
    assert "original bright red cartoon race car" in prompt
    assert "original friendly rusty tow truck" in prompt


@pytest.mark.parametrize(
    "payload",
    [
        {
            "worlds": ["cars"],
            "characters": [
                "lightning-mcqueen",
                "mater",
                "sally",
                "cruz-ramirez",
                "jackson-storm",
            ],
            "action": "racing",
        },
        {
            "worlds": ["cars"],
            "characters": ["lightning-mcqueen"],
            "action": "racing",
            "custom_idea": "x" * 301,
        },
        {
            "characters": ["unicorn"],
            "action": "riding",
            "scenes": ["volcano"],
        },
    ],
)
def test_invalid_generation_requests_are_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)
