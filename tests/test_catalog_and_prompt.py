import pytest
from pydantic import ValidationError

from app.catalog import CHARACTER_BY_ID, catalog_payload
from app.prompting import build_image_prompt
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


def test_princess_on_unicorn_prompt_is_simple_and_printable() -> None:
    request = GenerationRequest(
        worlds=["princesses", "unicorns"],
        characters=["princess", "unicorn"],
        action="riding",
        custom_idea="princezná jazdí na jednorožcovi cez dúhový most",
        orientation="portrait",
    )

    prompt = build_image_prompt(request)

    assert "fairy-tale princess" in prompt
    assert "magical unicorn" in prompt
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

    assert "Zuma from PAW Patrol" in prompt
    assert "Rocky from PAW Patrol" in prompt
    assert "Skye from PAW Patrol" in prompt
    assert "Mighty Pups superhero variant" in prompt
    assert "left to right" in prompt


def test_mcqueen_and_mater_prompt_uses_recognizable_names() -> None:
    request = GenerationRequest(
        worlds=["cars"],
        characters=["lightning-mcqueen", "mater"],
        action="racing",
        orientation="landscape",
    )

    prompt = build_image_prompt(request)

    assert "Lightning McQueen" in prompt
    assert "Mater, the rusty tow truck" in prompt
    assert "signature silhouette" in prompt


def test_kpop_demon_hunters_prompt_mentions_new_world_and_group() -> None:
    request = GenerationRequest(
        worlds=["kpop-demon-hunters"],
        characters=["rumi", "mira", "zoey", "huntrix"],
        action="rescuing",
        orientation="portrait",
    )

    prompt = build_image_prompt(request)

    assert "K-pop Demon Hunters" in prompt
    assert "Rumi" in prompt
    assert "Mira" in prompt
    assert "Zoey" in prompt
    assert "HUNTR/X" in prompt


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
            "worlds": ["princesses"],
            "characters": ["unicorn"],
            "action": "riding",
        },
    ],
)
def test_invalid_generation_requests_are_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)
