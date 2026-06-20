from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class World:
    id: str
    label: str
    icon: str
    color: str


@dataclass(frozen=True, slots=True)
class Character:
    id: str
    label: str
    prompt_name: str
    world_id: str
    icon: str


@dataclass(frozen=True, slots=True)
class Action:
    id: str
    label: str
    prompt_text: str
    icon: str


WORLDS = (
    World("princesses", "Princezné", "👸", "violet"),
    World("unicorns", "Jednorožce", "🦄", "pink"),
    World("rescue-pups", "Labková patrola", "🐾", "blue"),
    World("cars", "Autá", "🏎️", "coral"),
)

CHARACTERS = (
    Character("princess", "Princezná", "a cheerful young fairy-tale princess", "princesses", "👸"),
    Character("unicorn", "Jednorožec", "a friendly magical unicorn", "unicorns", "🦄"),
    Character("zuma", "Zuma", "Zuma from PAW Patrol", "rescue-pups", "🛟"),
    Character("rocky", "Rocky", "Rocky from PAW Patrol", "rescue-pups", "♻️"),
    Character("skye", "Skye", "Skye from PAW Patrol", "rescue-pups", "🚁"),
    Character("chase", "Chase", "Chase from PAW Patrol", "rescue-pups", "⭐"),
    Character("marshall", "Marshall", "Marshall from PAW Patrol", "rescue-pups", "🚒"),
    Character("rubble", "Rubble", "Rubble from PAW Patrol", "rescue-pups", "🚧"),
    Character(
        "mighty-pups",
        "Mighty Pups",
        "the selected PAW Patrol pups in their recognizable Mighty Pups superhero variant",
        "rescue-pups",
        "⚡",
    ),
    Character(
        "lightning-mcqueen",
        "Bleskový McQueen",
        "Lightning McQueen from Disney Pixar Cars",
        "cars",
        "🏁",
    ),
    Character(
        "mater",
        "Mater / Burák",
        "Mater, the rusty tow truck from Disney Pixar Cars",
        "cars",
        "🪝",
    ),
    Character("sally", "Sally", "Sally Carrera from Disney Pixar Cars", "cars", "💙"),
    Character(
        "cruz-ramirez",
        "Cruz Ramirez",
        "Cruz Ramirez from Disney Pixar Cars",
        "cars",
        "💛",
    ),
    Character(
        "jackson-storm",
        "Jackson Storm",
        "Jackson Storm from Disney Pixar Cars",
        "cars",
        "🌩️",
    ),
    Character("mack", "Mack", "Mack the transporter truck from Disney Pixar Cars", "cars", "🚛"),
)

ACTIONS = (
    Action("riding", "Jazdia", "riding together on a gentle adventure", "🦄"),
    Action("rescuing", "Zachraňujú", "performing a friendly rescue together", "🛡️"),
    Action("racing", "Pretekajú", "taking part in a cheerful, safe race", "🏁"),
)

WORLD_BY_ID = {item.id: item for item in WORLDS}
CHARACTER_BY_ID = {item.id: item for item in CHARACTERS}
ACTION_BY_ID = {item.id: item for item in ACTIONS}


def catalog_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "worlds": [asdict(item) for item in WORLDS],
        "characters": [asdict(item) for item in CHARACTERS],
        "actions": [asdict(item) for item in ACTIONS],
    }

