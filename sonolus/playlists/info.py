import random

from fastapi import APIRouter

from core import SonolusRequest
from helpers.data_compilers import compile_engines_list
from helpers.level_builder import fetch_music_data, get_merged_musics
from helpers.playlist_builder import build_playlist_item
from helpers.models.sonolus.item_section import PlaylistItemSection
from helpers.models.sonolus.options import ServerForm, ServerTextOption
from helpers.models.sonolus.response import ServerItemInfo

router = APIRouter()


@router.get("", response_model=ServerItemInfo)
async def main(request: SonolusRequest):
    locale = request.state.loc
    localization = request.state.localization
    api = request.app.api
    source = request.app.base_url

    music_data = await fetch_music_data(api)
    musics = get_merged_musics(
        music_data, request.state.show_spoilers, request.state.localization
    )
    engines = await request.app.run_blocking(compile_engines_list, source, localization)

    if not engines or not musics:
        return ServerItemInfo(sections=[], banner=None)

    engine = engines[0]

    newest_musics = sorted(musics, key=lambda m: m.published_at, reverse=True)[:5]
    newest = []
    for music in newest_musics:
        if not music.vocals or not music.difficulties:
            continue
        playlist = await build_playlist_item(
            music=music,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
        )
        newest.append(playlist)

    random_musics = random.sample(musics, min(5, len(musics)))
    random_playlists = []
    for music in random_musics:
        if not music.vocals or not music.difficulties:
            continue
        playlist = await build_playlist_item(
            music=music,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
        )
        random_playlists.append(playlist)

    sections = []
    if newest:
        sections.append(
            PlaylistItemSection(
                title="#NEWEST",
                icon="clock",
                items=newest,
            )
        )
    if random_playlists:
        sections.append(
            PlaylistItemSection(
                title="#RANDOM",
                icon="shuffle",
                items=random_playlists,
            )
        )

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
    ]

    return ServerItemInfo(
        searches=searches,
        sections=sections,
        banner=None,
    )
