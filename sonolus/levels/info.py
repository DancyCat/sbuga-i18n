import random

from fastapi import APIRouter, HTTPException, status

from core import SonolusRequest
from helpers.data_compilers import compile_engines_list
from helpers.level_builder import (
    fetch_music_data,
    get_merged_musics,
    build_level_item,
    has_music_data,
)
from helpers.search import get_all_artists, get_all_captions, get_level_range
from helpers.models.api.music import translate_caption
from helpers.models.sonolus.item_section import LevelItemSection
from helpers.models.sonolus.options import (
    ServerForm,
    ServerMultiOption,
    ServerSelectOption,
    ServerSliderOption,
    ServerTextOption,
    ServerToggleOption,
    ServerOption_Value,
)
from helpers.models.sonolus.response import ServerItemInfo

router = APIRouter()


@router.get("", response_model=ServerItemInfo)
async def main(request: SonolusRequest):
    locale = request.state.loc
    localization = request.state.localization
    api = request.app.api
    source = request.app.base_url

    if not has_music_data():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=locale.data_loading
        )

    music_data = await fetch_music_data(api)
    musics = get_merged_musics(
        music_data, request.state.show_spoilers, request.state.localization
    )
    engines = await request.app.run_blocking(compile_engines_list, source, localization)

    if not engines or not musics:
        return ServerItemInfo(sections=[], banner=None)

    engine = engines[0]

    random_musics = random.sample(musics, min(5, len(musics)))
    random_levels = []
    for music in random_musics:
        if not music.vocals or not music.difficulties:
            continue
        vocal = music.vocals[0]
        diff = music.difficulties[-1]
        level = build_level_item(
            music=music,
            vocal=vocal,
            difficulty_name=diff.difficulty,
            play_level=diff.play_level,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
            levelbg=request.state.levelbg,
            spoiler_tag=locale.spoiler,
        )
        random_levels.append(level)

    newest_musics = sorted(musics, key=lambda m: m.published_at, reverse=True)[:5]
    newest_levels = []
    for music in newest_musics:
        if not music.vocals or not music.difficulties:
            continue
        vocal = music.vocals[0]
        diff = music.difficulties[-1]
        level = build_level_item(
            music=music,
            vocal=vocal,
            difficulty_name=diff.difficulty,
            play_level=diff.play_level,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
            levelbg=request.state.levelbg,
            spoiler_tag=locale.spoiler,
        )
        newest_levels.append(level)

    sections = []
    if newest_levels:
        sections.append(
            LevelItemSection(title="#NEWEST", icon="clock", items=newest_levels)
        )
    if random_levels:
        sections.append(
            LevelItemSection(title="#RANDOM", icon="shuffle", items=random_levels)
        )

    min_lv, max_lv = get_level_range()

    all_artists = get_all_artists()
    artist_values = [ServerOption_Value(name=a, title=a) for a in all_artists]

    all_captions = get_all_captions()
    caption_values = [
        ServerOption_Value(name=c, title=translate_caption(c, localization))
        for c in all_captions
    ]

    searches = [
        ServerForm(
            type="quick",
            title="#KEYWORDS",
            icon="search",
            requireConfirmation=False,
            options=[
                ServerTextOption(
                    query="keywords",
                    name="#KEYWORDS",
                    required=False,
                    default="",
                    placeholder="#KEYWORDS_PLACEHOLDER",
                    limit=100,
                    shortcuts=[],
                ),
            ],
        ),
        ServerForm(
            type="advanced",
            title="#ADVANCED",
            icon="advanced",
            requireConfirmation=False,
            options=[
                ServerTextOption(
                    query="keywords",
                    name="#KEYWORDS",
                    required=False,
                    default="",
                    placeholder="#KEYWORDS_PLACEHOLDER",
                    limit=100,
                    shortcuts=[],
                ),
                ServerToggleOption(
                    query="random",
                    name="#RANDOM",
                    required=False,
                    default=False,
                ),
                *(
                    [
                        ServerMultiOption(
                            query="artists",
                            name="#ARTISTS",
                            required=False,
                            default=[True] * len(artist_values),
                            values=artist_values,
                        )
                    ]
                    if artist_values
                    else []
                ),
                *(
                    [
                        ServerMultiOption(
                            query="category",
                            name="#CATEGORY",
                            required=False,
                            default=[True] * len(caption_values),
                            values=caption_values,
                        )
                    ]
                    if caption_values
                    else []
                ),
                ServerSelectOption(
                    query="difficulty",
                    name="#DIFFICULTY",
                    required=False,
                    default="all",
                    values=[
                        ServerOption_Value(name="all", title="#ANY"),
                        ServerOption_Value(name="easy", title="#EASY"),
                        ServerOption_Value(name="normal", title="#NORMAL"),
                        ServerOption_Value(name="hard", title="#HARD"),
                        ServerOption_Value(name="expert", title="#EXPERT"),
                        ServerOption_Value(name="master", title="#MASTER"),
                        ServerOption_Value(name="append", title="#SPECIAL"),
                    ],
                ),
                ServerSliderOption(
                    query="minrating",
                    name="#RATING_MINIMUM",
                    required=False,
                    default=min_lv,
                    min=min_lv,
                    max=max_lv,
                    step=1,
                ),
                ServerSliderOption(
                    query="maxrating",
                    name="#RATING_MAXIMUM",
                    required=False,
                    default=max_lv,
                    min=min_lv,
                    max=max_lv,
                    step=1,
                ),
                ServerSelectOption(
                    query="sort",
                    name="#SORT",
                    required=False,
                    default="published_at",
                    values=[
                        ServerOption_Value(name="published_at", title="#NEWEST"),
                        ServerOption_Value(name="rating", title="#RATING"),
                        ServerOption_Value(name="title", title="#TITLE"),
                    ],
                ),
                ServerSelectOption(
                    query="order",
                    name="#SORT",
                    description="Ascending or Descending",
                    required=False,
                    default="desc",
                    values=[
                        ServerOption_Value(name="desc", title="Descending"),
                        ServerOption_Value(name="asc", title="Ascending"),
                    ],
                ),
            ],
        ),
    ]

    return ServerItemInfo(
        searches=searches,
        sections=sections,
        banner=None,
    )
