from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .catalog import ACTION_BY_ID, CHARACTER_BY_ID, WORLD_BY_ID

Orientation = Literal["portrait", "landscape"]
GenerationMode = Literal["line_art_direct", "color_first"]
ComicStoryType = Literal["trip", "rescue", "race", "surprise", "calm_day"]
ComicPrimaryMode = Literal["line_art", "color"]


class GenerationRequest(BaseModel):
    worlds: list[str] = Field(min_length=1, max_length=4)
    characters: list[str] = Field(default_factory=list, max_length=4)
    action: str
    custom_idea: str = Field(default="", max_length=300)
    orientation: Orientation = "portrait"
    generation_mode: GenerationMode = "line_art_direct"

    @field_validator("worlds")
    @classmethod
    def validate_worlds(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Svety sa nesmú opakovať.")
        unknown = [value for value in values if value not in WORLD_BY_ID]
        if unknown:
            raise ValueError(f"Neznáme svety: {', '.join(unknown)}")
        return values

    @field_validator("characters")
    @classmethod
    def validate_characters(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Postavy sa nesmú opakovať.")
        unknown = [value for value in values if value not in CHARACTER_BY_ID]
        if unknown:
            raise ValueError(f"Neznáme postavy: {', '.join(unknown)}")
        return values

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in ACTION_BY_ID:
            raise ValueError("Neznáma akcia.")
        return value

    @field_validator("custom_idea")
    @classmethod
    def normalize_custom_idea(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_character_worlds(self) -> "GenerationRequest":
        if not self.characters:
            return self
        selected_worlds = set(self.worlds)
        missing_worlds = {
            CHARACTER_BY_ID[character_id].world_id
            for character_id in self.characters
            if CHARACTER_BY_ID[character_id].world_id not in selected_worlds
        }
        if missing_worlds:
            labels = ", ".join(WORLD_BY_ID[item].label for item in sorted(missing_worlds))
            raise ValueError(f"Pre vybrané postavy chýbajú svety: {labels}.")
        return self


class GenerationStatus(BaseModel):
    id: int
    status: Literal["queued", "running", "done", "failed"]
    request: GenerationRequest
    error: str | None = None
    png_url: str | None = None
    pdf_url: str | None = None
    color_url: str | None = None
    print_url: str | None = None
    pattern_print_url: str | None = None


class ComicRequest(BaseModel):
    worlds: list[str] = Field(min_length=1, max_length=4)
    characters: list[str] = Field(default_factory=list, max_length=4)
    story_type: ComicStoryType = "trip"
    custom_idea: str = Field(default="", max_length=300)
    primary_mode: ComicPrimaryMode = "line_art"

    @field_validator("worlds")
    @classmethod
    def validate_worlds(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Svety sa nesmú opakovať.")
        unknown = [value for value in values if value not in WORLD_BY_ID]
        if unknown:
            raise ValueError(f"Neznáme svety: {', '.join(unknown)}")
        return values

    @field_validator("characters")
    @classmethod
    def validate_characters(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Postavy sa nesmú opakovať.")
        unknown = [value for value in values if value not in CHARACTER_BY_ID]
        if unknown:
            raise ValueError(f"Neznáme postavy: {', '.join(unknown)}")
        return values

    @field_validator("custom_idea")
    @classmethod
    def normalize_custom_idea(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_character_worlds(self) -> "ComicRequest":
        if not self.characters:
            return self
        selected_worlds = set(self.worlds)
        missing_worlds = {
            CHARACTER_BY_ID[character_id].world_id
            for character_id in self.characters
            if CHARACTER_BY_ID[character_id].world_id not in selected_worlds
        }
        if missing_worlds:
            labels = ", ".join(WORLD_BY_ID[item].label for item in sorted(missing_worlds))
            raise ValueError(f"Pre vybrané postavy chýbajú svety: {labels}.")
        return self


class ComicPageStatus(BaseModel):
    page_number: int
    color_url: str | None = None
    line_art_url: str | None = None


class ComicStatus(BaseModel):
    id: int
    status: Literal["queued", "running", "done", "failed"]
    request: ComicRequest
    error: str | None = None
    pages: list[ComicPageStatus] = Field(default_factory=list)
    color_pdf_url: str | None = None
    line_art_pdf_url: str | None = None
    print_url: str | None = None
