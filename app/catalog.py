from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class World:
    id: str
    label: str
    icon: str
    color: str
    asset: str
    prompt_name: str


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


@dataclass(frozen=True, slots=True)
class Scene:
    id: str
    label: str
    prompt_text: str
    icon: str


WORLDS = (
    World("princesses", "Princezné", "👸", "violet", "/static/assets/world-princesses.png", "an original fairy-tale world"),
    World("unicorns", "Jednorožce", "🦄", "pink", "/static/assets/world-unicorns.png", "an original magical-animal world"),
    World("rescue-pups", "Labková patrola", "🐾", "blue", "/static/assets/world-rescue-pups.png", "an original friendly rescue-team world"),
    World("cars", "Autá", "🏎️", "coral", "/static/assets/world-cars.png", "an original cartoon racing world"),
    World(
        "kpop-demon-hunters",
        "K-pop Demon Hunters",
        "🎤",
        "magenta",
        "/static/assets/world-kpop-demon-hunters.svg",
        "an original pop-star adventure world",
    ),
)

CHARACTERS = (
    Character("princess", "Princezná", "an original cheerful fairy-tale child character", "princesses", "👸"),
    Character("unicorn", "Jednorožec", "an original friendly magical unicorn", "unicorns", "🦄"),
    Character("zuma", "Zuma", "an original orange rescue puppy", "rescue-pups", "🛟"),
    Character("rocky", "Rocky", "an original green recycling puppy", "rescue-pups", "♻️"),
    Character("skye", "Skye", "an original pink flying puppy", "rescue-pups", "🚁"),
    Character("chase", "Chase", "an original blue police puppy", "rescue-pups", "⭐"),
    Character("marshall", "Marshall", "an original red firefighter puppy", "rescue-pups", "🚒"),
    Character("rubble", "Rubble", "an original yellow builder puppy", "rescue-pups", "🚧"),
    Character(
        "mighty-pups",
        "Mighty Pups",
        "the selected original rescue puppies in a bright superhero variant",
        "rescue-pups",
        "⚡",
    ),
    Character(
        "lightning-mcqueen",
        "Bleskový McQueen",
        "an original bright red cartoon race car with expressive eyes",
        "cars",
        "🏁",
    ),
    Character(
        "mater",
        "Mater / Burák",
        "an original friendly rusty tow truck with expressive eyes",
        "cars",
        "🪝",
    ),
    Character("sally", "Sally", "an original blue cartoon sports car with expressive eyes", "cars", "💙"),
    Character(
        "cruz-ramirez",
        "Cruz Ramirez",
        "an original yellow cartoon race car with expressive eyes",
        "cars",
        "💛",
    ),
    Character(
        "jackson-storm",
        "Jackson Storm",
        "an original dark futuristic cartoon race car with expressive eyes",
        "cars",
        "🌩️",
    ),
    Character("mack", "Mack", "an original large cartoon transporter truck with expressive eyes", "cars", "🚛"),
    Character("rumi", "Rumi", "an original confident young pop singer and adventurer", "kpop-demon-hunters", "🎤"),
    Character("mira", "Mira", "an original stylish young pop singer and adventurer", "kpop-demon-hunters", "✨"),
    Character("zoey", "Zoey", "an original bright playful young pop singer and adventurer", "kpop-demon-hunters", "🌙"),
    Character(
        "huntrix",
        "HUNTR/X",
        "three original young pop singers and adventurers together",
        "kpop-demon-hunters",
        "🎶",
    ),
)

CHARACTER_THEMES = (
    ("fairytales", "Rozprávky", ("princess", "unicorn")),
    ("paw-patrol", "Labková patrola", ("zuma", "rocky", "skye", "chase", "marshall", "rubble", "mighty-pups")),
    ("cars", "Autá", ("lightning-mcqueen", "mater", "sally", "cruz-ramirez", "jackson-storm", "mack")),
    ("demon-hunters", "Demon Hunters", ("rumi", "mira", "zoey", "huntrix")),
)

SCENES = (
    Scene("castle", "Hrad", "a simple friendly castle", "🏰"),
    Scene("city", "Mesto", "a simple cheerful city street", "🏙️"),
    Scene("forest", "Les", "a simple friendly forest", "🌲"),
    Scene("park", "Park", "a simple sunny park", "🌳"),
    Scene("beach", "Pláž", "a simple calm beach", "🏖️"),
)

ACTIONS = (
    Action("riding", "Jazdia", "riding together on a gentle adventure", "🦄"),
    Action("rescuing", "Zachraňujú", "performing a friendly rescue together", "🛡️"),
    Action("racing", "Pretekajú", "taking part in a cheerful, safe race", "🏁"),
)

WORLD_BY_ID = {item.id: item for item in WORLDS}
CHARACTER_BY_ID = {item.id: item for item in CHARACTERS}
ACTION_BY_ID = {item.id: item for item in ACTIONS}
SCENE_BY_ID = {item.id: item for item in SCENES}


def catalog_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "worlds": [asdict(item) for item in WORLDS],
        "characters": [asdict(item) for item in CHARACTERS],
        "actions": [asdict(item) for item in ACTIONS],
        "character_themes": [
            {
                "id": theme_id,
                "label": label,
                "characters": [asdict(CHARACTER_BY_ID[character_id]) for character_id in character_ids],
            }
            for theme_id, label, character_ids in CHARACTER_THEMES
        ],
        "scenes": [asdict(item) for item in SCENES],
    }
