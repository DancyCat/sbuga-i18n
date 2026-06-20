from fastapi import APIRouter, HTTPException, status

from core import SonolusRequest
from helpers.data_compilers import compile_engines_list
from helpers.level_builder import fetch_music_data, get_merged_musics
from helpers.playlist_builder import (
    parse_playlist_id,
    build_playlist_item,
    build_playlist_description,
)
from helpers.models.sonolus.response import ServerItemDetails

router = APIRouter()


@router.get("", response_model=ServerItemDetails)
async def main(request: SonolusRequest, item_name: str):
    locale = request.state.loc
    api = request.app.api
    source = request.app.base_url
    localization = request.state.localization

    music_id = parse_playlist_id(item_name)
    if music_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=locale.not_found,
        )

    music_data = await fetch_music_data(api)
    musics = get_merged_musics(
        music_data, request.state.show_spoilers, request.state.localization
    )
    engines = await request.app.run_blocking(compile_engines_list, source, localization)

    if not engines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=locale.not_found,
        )

    engine = engines[0]

    music = next((m for m in musics if m.id == music_id), None)
    if not music or not music.vocals or not music.difficulties:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=locale.item_not_found("Playlist", item_name),
        )

    playlist = await build_playlist_item(
        music=music,
        engine=engine,
        source=source,
        localization=localization,
        music_data=music_data,
    )

    description = build_playlist_description(music, music_data=music_data)

    return ServerItemDetails(
        item=playlist,
        description=description,
        actions=[],
        hasCommunity=False,
        leaderboards=[],
        sections=[],
    )
