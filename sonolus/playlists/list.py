import math

from fastapi import APIRouter, HTTPException, status

from core import SonolusRequest
from helpers.data_compilers import compile_engines_list
from helpers.level_builder import (
    fetch_music_data,
    get_merged_musics,
    has_music_data,
)
from helpers.search import fuzzy_search_playlists
from helpers.playlist_builder import build_playlist_item
from helpers.models.sonolus.response import ServerItemList

router = APIRouter()


@router.get("", response_model=ServerItemList)
async def main(
    request: SonolusRequest,
    page: int = 0,
    keywords: str = "",
):
    api = request.app.api
    source = request.app.base_url
    locale = request.state.loc
    localization = request.state.localization
    items_per_page = request.app.get_items_per_page("playlists")

    if not has_music_data():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=locale.data_loading
        )

    music_data = await fetch_music_data(api)
    musics = get_merged_musics(
        music_data, request.state.show_spoilers, request.state.localization
    )
    engines = await request.app.run_blocking(compile_engines_list, source, localization)

    if not engines:
        return ServerItemList(pageCount=0, items=[])

    engine = engines[0]

    music_map = {m.id: m for m in musics}

    if keywords.strip():
        matched_ids = fuzzy_search_playlists(keywords)
        musics = [music_map[mid] for mid in matched_ids if mid in music_map]
    else:
        musics.sort(key=lambda m: m.published_at, reverse=True)

    musics = [m for m in musics if m.vocals and m.difficulties]

    total = len(musics)
    page_count = max(1, math.ceil(total / items_per_page))

    start = page * items_per_page
    page_musics = musics[start : start + items_per_page]

    items = []
    for music in page_musics:
        playlist = await build_playlist_item(
            music=music,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
        )
        items.append(playlist)

    return ServerItemList(pageCount=page_count, items=items)
