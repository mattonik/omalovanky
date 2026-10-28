import pytest
from pydantic import ValidationError

from app.catalog import CHARACTER_BY_ID, catalog_payload
from app.prompting import build_color_preview_prompt, build_image_prompt, build_line_art_edit_prompt, build_comic_page_prompts, generation_page_prompts
from app.schemas import ComicRequest, GenerationRequest


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

    assert "young princess wearing a small crown and a princess dress" in prompt
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

    assert "Zuma from PAW Patrol" in prompt
    assert "Rocky from PAW Patrol" in prompt
    assert "Skye from PAW Patrol" in prompt
    assert "Mighty Pups from PAW Patrol" in prompt
    assert "left to right" in prompt


def test_cars_prompt_uses_character_names() -> None:
    request = GenerationRequest(
        worlds=["cars"],
        characters=["lightning-mcqueen", "mater"],
        action="racing",
        orientation="landscape",
    )

    prompt = build_image_prompt(request)

    assert "Lightning McQueen from Cars" in prompt
    assert "Mater from Cars" in prompt
    assert "signature silhouette" in prompt


def test_prompt_names_selected_huntrix_characters() -> None:
    request = GenerationRequest(
        worlds=["kpop-demon-hunters"],
        characters=["rumi", "mira", "zoey", "huntrix"],
        action="rescuing",
        orientation="portrait",
    )

    prompt = build_image_prompt(request)

    assert "Rumi from KPop Demon Hunters" in prompt
    assert "HUNTR/X from KPop Demon Hunters" in prompt
    assert "Worlds:" not in prompt


def test_character_selection_derives_its_theme() -> None:
    request = GenerationRequest(
        characters=["unicorn"],
        action="riding",
    )

    prompt = build_image_prompt(request)

    assert request.worlds == ["unicorns"]
    assert "magical unicorn" in prompt
    assert "Worlds:" not in prompt


def test_generation_defaults_to_landscape_without_background() -> None:
    request = GenerationRequest(characters=["mater"], action="racing")
    prompt = build_image_prompt(request)

    assert request.orientation == "landscape"
    assert "Background: plain white background with no scenery or extra objects." in prompt
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
    assert "Lightning McQueen from Cars" in prompt
    assert "Mater from Cars" in prompt


def test_named_characters_are_used_in_every_prompt_path() -> None:
    request = GenerationRequest(characters=["skye", "huntrix"], action="playing")
    prompts = [build_image_prompt(request), build_color_preview_prompt(request), build_line_art_edit_prompt(request)]
    prompts += build_comic_page_prompts(ComicRequest(characters=request.characters))
    assert all("Skye from PAW Patrol" in prompt and "HUNTR/X from KPop Demon Hunters" in prompt for prompt in prompts)
    assert all("Worlds:" not in prompt for prompt in prompts)


def test_generic_retry_uses_descriptions_across_all_prompt_paths() -> None:
    request = GenerationRequest(characters=["skye", "huntrix"], action="playing", generic_characters=True)
    prompts = [build_image_prompt(request), build_color_preview_prompt(request), build_line_art_edit_prompt(request)]
    prompts += build_comic_page_prompts(ComicRequest(characters=request.characters, generic_characters=True))
    assert all("pink flying rescue puppy" in prompt and "group of three young pop singers" in prompt for prompt in prompts)
    assert all("PAW Patrol" not in prompt and "HUNTR/X" not in prompt for prompt in prompts)


@pytest.mark.parametrize(("level", "phrase"), [
    ("simple", "large closed areas for crayons"),
    ("medium", "moderately detailed shapes"),
    ("detailed", "intricate but readable shapes"),
])
def test_complexity_applies_to_generation_and_edit(level: str, phrase: str) -> None:
    request = GenerationRequest(characters=["skye"], action="playing", complexity=level)
    assert all(phrase in prompt for prompt in (build_image_prompt(request), build_color_preview_prompt(request), build_line_art_edit_prompt(request)))
    assert GenerationRequest.model_validate({"action": "playing"}).complexity == "simple"


def test_invalid_complexity_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(action="playing", complexity="unknown")


def test_multiple_pages_have_distinct_scene_directions() -> None:
    request = GenerationRequest(characters=["princess", "skye"], scenes=["beach"], action="playing", page_count=6)
    prompts = generation_page_prompts(request, build_image_prompt(request))
    assert len(prompts) == 6
    assert len(set(prompts)) == 6
    assert "begin their shared activity" in prompts[0]
    assert "explore and discover something surprising" in prompts[1]
    assert all("Skye from PAW Patrol" in prompt and "a simple calm beach" in prompt for prompt in prompts)
    single = request.model_copy(update={"page_count": 1})
    assert generation_page_prompts(single, "original prompt") == ["original prompt"]


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
