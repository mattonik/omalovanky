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
    Character("princess", "Princezná", "an original cheerful young princess wearing a small crown and a princess dress", "princesses", "👸"),
    Character("unicorn", "Jednorožec", "an original friendly magical unicorn", "unicorns", "🦄"),
    Character("zuma", "Zuma", "Zuma from PAW Patrol", "rescue-pups", "🛟"),
    Character("rocky", "Rocky", "Rocky from PAW Patrol", "rescue-pups", "♻️"),
    Character("skye", "Skye", "Skye from PAW Patrol", "rescue-pups", "🚁"),
    Character("chase", "Chase", "Chase from PAW Patrol", "rescue-pups", "⭐"),
    Character("marshall", "Marshall", "Marshall from PAW Patrol", "rescue-pups", "🚒"),
    Character("rubble", "Rubble", "Rubble from PAW Patrol", "rescue-pups", "🚧"),
    Character(
        "mighty-pups",
        "Mighty Pups",
        "Mighty Pups from PAW Patrol",
        "rescue-pups",
        "⚡",
    ),
    Character(
        "lightning-mcqueen",
        "Bleskový McQueen",
        "Lightning McQueen from Cars",
        "cars",
        "🏁",
    ),
    Character(
        "mater",
        "Mater / Burák",
        "Mater from Cars",
        "cars",
        "🪝",
    ),
    Character("sally", "Sally", "Sally from Cars", "cars", "💙"),
    Character(
        "cruz-ramirez",
        "Cruz Ramirez",
        "Cruz Ramirez from Cars",
        "cars",
        "💛",
    ),
    Character(
        "jackson-storm",
        "Jackson Storm",
        "Jackson Storm from Cars",
        "cars",
        "🌩️",
    ),
    Character("mack", "Mack", "Mack from Cars", "cars", "🚛"),
    Character("rumi", "Rumi", "Rumi from KPop Demon Hunters", "kpop-demon-hunters", "🎤"),
    Character("mira", "Mira", "Mira from KPop Demon Hunters", "kpop-demon-hunters", "✨"),
    Character("zoey", "Zoey", "Zoey from KPop Demon Hunters", "kpop-demon-hunters", "🌙"),
    Character(
        "huntrix",
        "HUNTR/X",
        "HUNTR/X from KPop Demon Hunters",
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
    Action("playing", "Hrajú sa", "playing happily together", "⚽"),
    Action("exploring", "Objavujú", "exploring together with curiosity", "🔎"),
    Action("building", "Stavajú", "building something together", "🧱"),
    Action("dancing", "Tancujú", "dancing happily together", "🎵"),
    Action("resting", "Oddychujú", "resting peacefully together", "☀️"),
    Action("riding", "Jazdia", "riding together on a gentle adventure", "🦄"),
    Action("rescuing", "Zachraňujú", "performing a friendly rescue together", "🛡️"),
    Action("racing", "Pretekajú", "taking part in a cheerful, safe race", "🏁"),
)

WORLD_BY_ID = {item.id: item for item in WORLDS}
CHARACTER_BY_ID = {item.id: item for item in CHARACTERS}
GENERIC_CHARACTERS = {
    "zuma": "an orange rescue puppy", "rocky": "a green recycling puppy",
    "skye": "a pink flying rescue puppy", "chase": "a blue police puppy",
    "marshall": "a red firefighter puppy", "rubble": "a yellow builder puppy",
    "mighty-pups": "a team of superhero rescue puppies",
    "lightning-mcqueen": "a red cartoon race car", "mater": "a friendly rusty tow truck",
    "sally": "a blue cartoon sports car", "cruz-ramirez": "a yellow cartoon race car",
    "jackson-storm": "a dark futuristic race car", "mack": "a large transporter truck",
    "rumi": "a confident young pop singer", "mira": "a stylish young pop singer",
    "zoey": "a playful young pop singer", "huntrix": "a group of three young pop singers",
}
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
