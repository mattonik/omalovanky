from __future__ import annotations

from .catalog import ACTION_BY_ID, CHARACTER_BY_ID, WORLD_BY_ID
from .schemas import ComicRequest, GenerationRequest

COMIC_STORY_TYPES = {
    "trip": (
        "Výlet",
        (
            "getting ready for a small trip",
            "noticing a friendly surprise on the path",
            "helping each other continue",
            "finding a cheerful place to rest",
            "sharing a happy moment together",
            "going home content and calm",
        ),
    ),
    "rescue": (
        "Záchrana",
        (
            "spotting someone who needs gentle help",
            "making a simple safe plan",
            "working together kindly",
            "solving the small problem",
            "celebrating the rescue",
            "everyone waving goodbye happily",
        ),
    ),
    "race": (
        "Preteky",
        (
            "getting ready for a friendly race",
            "starting slowly and safely",
            "encouraging each other",
            "passing a funny obstacle",
            "finishing together",
            "resting proudly after the race",
        ),
    ),
    "surprise": (
        "Prekvapenie",
        (
            "finding a mysterious friendly clue",
            "following it with curiosity",
            "meeting a helpful friend",
            "opening a small cheerful surprise",
            "sharing the surprise",
            "ending with a cozy happy scene",
        ),
    ),
    "calm_day": (
        "Pokojný deň",
        (
            "starting a quiet happy morning",
            "playing gently together",
            "noticing something beautiful nearby",
            "making or fixing something simple",
            "sharing a snack or rest",
            "ending the day peacefully",
        ),
    ),
}


def build_image_prompt(request: GenerationRequest) -> str:
    worlds = [WORLD_BY_ID[item].label for item in request.worlds]
    if len(worlds) == 1:
        world_text = worlds[0]
    else:
        world_text = ", ".join(worlds[:-1]) + f", and {worlds[-1]}"
    characters = [CHARACTER_BY_ID[item].prompt_name for item in request.characters]
    if characters:
        if len(characters) == 1:
            character_text = characters[0]
        else:
            character_text = ", ".join(characters[:-1]) + f", and {characters[-1]}"
        subjects = f"Subjects: {character_text}."
        subject_guidance = (
            "Show every requested subject once and keep all subjects fully visible."
        )
        recognition_guidance = (
            "The named characters must be immediately recognizable through their signature"
            " silhouette, face, costume or vehicle shape, while remaining a clean"
            " coloring-book drawing."
        )
    else:
        subjects = "Characters: none selected."
        subject_guidance = (
            "No specific characters were selected, so create a single clear scene that reads"
            " immediately as the chosen worlds and action."
        )
        recognition_guidance = (
            "Use the selected worlds as the visual anchor for the scene."
        )

    action = ACTION_BY_ID[request.action].prompt_text
    custom = (
        f"Additional scene direction: {request.custom_idea}."
        if request.custom_idea
        else "Keep the scene focused on one simple action."
    )
    composition = (
        "portrait composition with the subjects centered vertically"
        if request.orientation == "portrait"
        else "landscape composition with the subjects arranged clearly from left to right"
    )

    return f"""
Create one printable children's coloring page for ages 3 to 5.

Worlds: {world_text}.
{subjects}
Action: {action}.
{custom}
Use a {composition}.

{subject_guidance}
{recognition_guidance}
When multiple worlds are selected, blend their iconic visual cues naturally in one simple scene.

Art requirements:
- pure black line art on a pure white background
- thick, smooth, consistent outlines
- very simple friendly shapes and large closed areas for crayons
- minimal background detail and generous empty space
- safe margins around the entire artwork
- no color, gray, shading, hatching, gradients, texture, or filled black regions
- no text, letters, numbers, speech bubbles, logos, watermarks, borders, or page decorations
- no scary expressions, danger, weapons, or visual clutter
- one flat printable page, not a mockup, photograph, poster, or book spread
""".strip()


def build_color_preview_prompt(request: GenerationRequest) -> str:
    worlds = [WORLD_BY_ID[item].label for item in request.worlds]
    if len(worlds) == 1:
        world_text = worlds[0]
    else:
        world_text = ", ".join(worlds[:-1]) + f", and {worlds[-1]}"
    characters = [CHARACTER_BY_ID[item].prompt_name for item in request.characters]
    if characters:
        if len(characters) == 1:
            character_text = characters[0]
        else:
            character_text = ", ".join(characters[:-1]) + f", and {characters[-1]}"
        subjects = f"Subjects: {character_text}."
    else:
        subjects = "Characters: none selected."

    action = ACTION_BY_ID[request.action].prompt_text
    composition = (
        "portrait composition with the subjects centered vertically"
        if request.orientation == "portrait"
        else "landscape composition with the subjects arranged clearly from left to right"
    )

    return f"""
Create a simple full-color children's reference illustration for ages 3 to 5.

Worlds: {world_text}.
{subjects}
Action: {action}.
Use a {composition}.

This is a friendly colored reference for a coloring page, so keep the same simple scene,
clear silhouettes, and readable composition. Use bright, cheerful colors and large obvious
shapes. If no specific characters were selected, let the scene clearly communicate the
chosen theme worlds.

Art requirements:
- full color on a clean white or softly tinted background
- simple shapes, bold readable forms, and no visual clutter
- no text, letters, numbers, speech bubbles, logos, watermarks, borders, or page decorations
- no scary expressions, danger, weapons, or visual clutter
- one flat printable page, not a mockup, photograph, poster, or book spread
""".strip()


def build_line_art_edit_prompt(request: GenerationRequest) -> str:
    worlds = [WORLD_BY_ID[item].label for item in request.worlds]
    if len(worlds) == 1:
        world_text = worlds[0]
    else:
        world_text = ", ".join(worlds[:-1]) + f", and {worlds[-1]}"
    characters = [CHARACTER_BY_ID[item].prompt_name for item in request.characters]
    if characters:
        if len(characters) == 1:
            character_text = characters[0]
        else:
            character_text = ", ".join(characters[:-1]) + f", and {characters[-1]}"
        subject_text = f"Subjects: {character_text}."
    else:
        subject_text = "Characters: none selected."

    return f"""
Convert the supplied colored children's illustration into a clean coloring-book page.

Worlds: {world_text}.
{subject_text}
Keep the same composition, pose, framing, and character identities as the supplied image.
Turn everything into pure black line art on a pure white background.

Art requirements:
- thick, smooth, consistent outlines
- very simple friendly shapes and large closed areas for crayons
- minimal background detail and generous empty space
- safe margins around the entire artwork
- no color, gray, shading, hatching, gradients, texture, or filled black regions
- no text, letters, numbers, speech bubbles, logos, watermarks, borders, or page decorations
- one flat printable page, not a mockup, photograph, poster, or book spread
""".strip()


def build_comic_page_prompts(request: ComicRequest) -> list[str]:
    worlds = [WORLD_BY_ID[item].label for item in request.worlds]
    world_text = worlds[0] if len(worlds) == 1 else ", ".join(worlds[:-1]) + f", and {worlds[-1]}"
    characters = [CHARACTER_BY_ID[item].prompt_name for item in request.characters]
    if characters:
        character_text = characters[0] if len(characters) == 1 else ", ".join(characters[:-1]) + f", and {characters[-1]}"
        subjects = f"Main recurring subjects: {character_text}."
        identity = "Keep the same subjects recognizable and visually consistent across the story."
    else:
        subjects = "Main recurring subjects: none selected."
        identity = "Use the selected worlds as recurring visual anchors across the story."
    story_label, beats = COMIC_STORY_TYPES[request.story_type]
    custom = (
        f"Parent's extra idea for the whole story: {request.custom_idea}."
        if request.custom_idea
        else "No extra parent idea was provided."
    )
    prompts = []
    for index, beat in enumerate(beats, start=1):
        prompts.append(
            f"""
Create page {index} of 6 for a wordless children's picture mini-comic for ages 3 to 5.

Story type: {story_label}.
Worlds: {world_text}.
{subjects}
Story beat for this page: {beat}.
{custom}

{identity}
This must work without reading. Show one clear action, expressive poses, and an obvious visual sequence.
Simple symbols such as hearts, stars, arrows, sparkles, or music notes are allowed when useful.

Art requirements:
- full-color friendly children's illustration on a clean light background
- simple bold shapes, readable silhouettes, and minimal background detail
- no text, letters, numbers, speech bubbles, logos, captions, watermarks, signs, or labels
- no scary expressions, danger, weapons, or clutter
- one flat square-ish panel illustration, not a book mockup, page layout, collage, poster, or grid
""".strip()
        )
    return prompts
