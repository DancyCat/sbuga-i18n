import gzip, json, os
from io import BytesIO
from typing import Any

from helpers.models.sonolus.item import (
    EngineItem,
    SkinItem,
    BackgroundItem,
    EffectItem,
    ParticleItem,
)
from helpers.models.sonolus.misc import SRL

from helpers.repository_map import repo

cached: dict[str, Any] = {
    "skins": None,
    "effects": None,
    "particles": None,
    "banner": None,
}


def clear_compile_cache(specific: str | None = None):
    global cached
    if specific:
        cached[specific] = None
    else:
        new_cached: dict[str, Any] = {}
        for k in cached.keys():
            new_cached[k] = None
        cached = new_cached.copy()


def compile_banner() -> SRL | None:
    if cached["banner"]:
        return cached["banner"]
    path = "files/banner/banner.png"
    if os.path.exists(path):
        hash = repo.add_file(path)
        cached["banner"] = repo.get_srl(hash)
        return cached["banner"]
    return None


def compile_effects_list(source: str = None) -> list[EffectItem]:
    if cached["effects"]:
        return cached["effects"]
    compiled_data_list = []
    for effect in os.listdir("files/effects"):
        if not os.path.isdir(os.path.join("files", "effects", effect)):
            continue

        with open(f"files/effects/{effect}/effect.json", "r", encoding="utf8") as f:
            effect_data: dict = json.load(f)
        if not effect_data.get("enabled", True):
            continue

        compiled_data = EffectItem(
            name=effect,
            source=source,
            version=effect_data["version"],
            title=effect_data["title"],
            subtitle=effect_data["subtitle"],
            author=effect_data["author"],
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/effects/{effect}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/effects/{effect}/data")),
            audio=repo.get_srl(repo.add_file(f"files/effects/{effect}/audio")),
        )
        compiled_data_list.append(compiled_data)
    cached["effects"] = compiled_data_list
    return compiled_data_list


def compile_backgrounds_list(
    source: str = None, include_hidden: bool = False
) -> list[BackgroundItem]:
    cache_key = "backgrounds_all" if include_hidden else "backgrounds"
    if cached.get(cache_key):
        return cached[cache_key]
    compiled_data_list = []
    for background in os.listdir("files/backgrounds"):
        if not os.path.isdir(os.path.join("files", "backgrounds", background)):
            continue

        with open(
            f"files/backgrounds/{background}/background.json", "r", encoding="utf8"
        ) as f:
            background_data: dict = json.load(f)
        if not background_data.get("enabled", True):
            continue
        if not include_hidden and background_data.get("hidden", False):
            continue

        compiled_data = BackgroundItem(
            name=background,
            source=source,
            version=background_data["version"],
            title=background_data["title"],
            subtitle=background_data["subtitle"],
            author=background_data["author"],
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/backgrounds/{background}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/backgrounds/{background}/data")),
            image=repo.get_srl(
                repo.add_file(f"files/backgrounds/{background}/image.png")
            ),
            configuration=repo.get_srl(
                repo.add_file(f"files/backgrounds/{background}/configuration.json.gz")
            ),
        )
        compiled_data_list.append(compiled_data)
    cached[cache_key] = compiled_data_list
    return compiled_data_list


def compile_particles_list(source: str = None) -> list[ParticleItem]:
    if cached["particles"]:
        return cached["particles"]
    compiled_data_list: list[tuple[int, ParticleItem]] = []
    for particle in os.listdir("files/particles"):
        if not os.path.isdir(os.path.join("files", "particles", particle)):
            continue

        with open(
            f"files/particles/{particle}/particle.json", "r", encoding="utf8"
        ) as f:
            particle_data: dict = json.load(f)
        if not particle_data.get("enabled", True):
            continue

        compiled_data = ParticleItem(
            name=particle,
            source=source,
            version=particle_data["version"],
            title=particle_data["title"],
            subtitle=particle_data["subtitle"],
            author=particle_data["author"],
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/particles/{particle}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/particles/{particle}/data")),
            texture=repo.get_srl(repo.add_file(f"files/particles/{particle}/texture")),
        )
        compiled_data_list.append((particle_data.get("order", 0), compiled_data))
    compiled_data_list.sort(key=lambda d: (d[0], d[1].title))
    result = [item for _, item in compiled_data_list]
    cached["particles"] = result
    return result


class ExtendedSkinItem(SkinItem):
    locale: str | None = None
    engines: list[str] = []
    order: int = 0

    def to_skin_item(self) -> SkinItem:
        return SkinItem.model_validate(self.model_dump())

    def matches_locale(self, localization: str) -> bool:
        if self.locale is None:
            return True
        if self.locale.startswith("!"):
            return localization != self.locale[1:]
        return localization == self.locale


def compile_skins_list(source: str = None) -> list[ExtendedSkinItem]:
    if cached["skins"]:
        return cached["skins"]
    compiled_data_list: list[ExtendedSkinItem] = []
    for skin in os.listdir("files/skins"):
        if not os.path.isdir(os.path.join("files", "skins", skin)):
            continue

        with open(f"files/skins/{skin}/skin.json", "r", encoding="utf8") as f:
            skin_data: dict = json.load(f)
        if not skin_data.get("enabled", True):
            continue

        compiled_data = ExtendedSkinItem(
            name=skin,
            source=source,
            version=skin_data["version"],
            title=skin_data["title"],
            subtitle=skin_data.get("subtitle", ""),
            author=skin_data.get("author", ""),
            tags=[],
            thumbnail=repo.get_srl(repo.add_file(f"files/skins/{skin}/thumbnail.png")),
            data=repo.get_srl(repo.add_file(f"files/skins/{skin}/data")),
            texture=repo.get_srl(repo.add_file(f"files/skins/{skin}/texture")),
            locale=skin_data.get("locale"),
            engines=skin_data.get("engines", []),
            order=skin_data.get("order", 0),
        )
        compiled_data_list.append(compiled_data)
    compiled_data_list = sorted(compiled_data_list, key=lambda d: (d.order, d.title))
    cached["skins"] = compiled_data_list
    return compiled_data_list


def get_skins_for_locale(source: str, localization: str) -> list[ExtendedSkinItem]:
    all_skins = compile_skins_list(source)
    return [s for s in all_skins if s.matches_locale(localization)]


class ExtendedEngineItem(EngineItem):
    engine_sort_order: int | float

    def to_engine_item(self) -> EngineItem:
        return EngineItem.model_validate(self.model_dump())


def compile_engines_list(
    source: str = None, locale: str = "en"
) -> list[ExtendedEngineItem]:
    if cached.get(f"engines_{locale}"):
        return cached[f"engines_{locale}"]
    compiled_data_list: list[ExtendedEngineItem] = []
    for engine in os.listdir("files/engines"):
        if not os.path.isdir(os.path.join("files", "engines", engine)):
            continue

        with open(f"files/engines/{engine}/engine.json", "r", encoding="utf8") as f:
            engine_data: dict = json.load(f)
        if not engine_data.get("enabled", True):
            continue

        config_overrides: dict[str, dict[str, Any]] = engine_data.get(
            "config_overrides", {}
        )
        if config_overrides:
            with gzip.open(
                f"files/engines/{engine}/EngineConfiguration", "rt", encoding="utf-8"
            ) as f:
                data = json.load(f)

            for option in data.get("options", []):
                name = option.get("name")
                if name in config_overrides:
                    for opt_key, value in config_overrides[name].items():
                        option[opt_key] = value

            bytes_io = BytesIO()
            with gzip.GzipFile(fileobj=bytes_io, mode="wb") as gzipped_file:
                json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
                gzipped_file.write(json_data)

            config_hash = repo.add_bytes(bytes_io.getvalue())
        else:
            config_hash = repo.add_file(f"files/engines/{engine}/EngineConfiguration")

        def get_skin_name(engine_data: dict, locale: str) -> str:
            if engine_data.get("skin_name_locale", {}).get(locale):
                return engine_data["skin_name_locale"][locale]
            return engine_data["skin_name"]

        try:
            skins = compile_skins_list(source)
            skin_data = next(
                skin
                for skin in skins
                if skin.name == get_skin_name(engine_data, locale)
            )
            effects = compile_effects_list(source)
            effect_data = next(
                effect
                for effect in effects
                if effect.name == engine_data["effect_name"]
            )
            particles = compile_particles_list(source)
            particle_data = next(
                particle
                for particle in particles
                if particle.name == engine_data["particle_name"]
            )
            backgrounds = compile_backgrounds_list(source)
            background_data = next(
                background
                for background in backgrounds
                if background.name == engine_data["background_name"]
            )
        except StopIteration:
            raise KeyError(
                "incorrect key name, make sure engine file names and resource file names match"
            )

        compiled_data = ExtendedEngineItem(
            name=engine,
            title=engine_data.get("title"),
            subtitle=engine_data.get("subtitle"),
            source=source,
            author=engine_data.get("author"),
            tags=[],
            description=engine_data.get("description"),
            skin=skin_data.to_skin_item(),
            background=background_data,
            effect=effect_data,
            particle=particle_data,
            thumbnail=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/thumbnail.png")
            ),
            playData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EnginePlayData")
            ),
            watchData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EngineWatchData")
            ),
            previewData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EnginePreviewData")
            ),
            tutorialData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EngineTutorialData")
            ),
            rom=repo.get_srl(
                repo.add_file(
                    f"files/engines/{engine}/EngineRom",
                    error_on_file_nonexistent=False,
                )
            ),
            configuration=repo.get_srl(config_hash),
            engine_sort_order=engine_data.get("engine_sort_order", float("inf")),
        )

        compiled_data_list.append(compiled_data)
    compiled_data_list = sorted(
        compiled_data_list,
        key=lambda item: (item.engine_sort_order, item.title.lower()),
    )
    cached[f"engines_{locale}"] = compiled_data_list
    return compiled_data_list
