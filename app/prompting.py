from __future__ import annotations

from .catalog import ACTION_BY_ID, CHARACTER_BY_ID
from .schemas import GenerationRequest


def build_image_prompt(request: GenerationRequest) -> str:
    characters = [CHARACTER_BY_ID[item].prompt_name for item in request.characters]
    if len(characters) == 1:
        character_text = characters[0]
    else:
        character_text = ", ".join(characters[:-1]) + f", and {characters[-1]}"

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

Subjects: {character_text}.
Action: {action}.
{custom}
Use a {composition}.

The named characters must be immediately recognizable through their signature silhouette,
face, costume or vehicle shape, while remaining a clean coloring-book drawing. Show every
requested subject once and keep all subjects fully visible.

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

