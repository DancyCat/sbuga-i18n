import math
import random as rand_module


from fastapi import APIRouter, HTTPException, status

from core import SonolusRequest
from helpers.data_compilers import compile_engines_list
from helpers.level_builder import (
    fetch_music_data,
    get_merged_musics,
    build_level_item,
    has_music_data,
)
from helpers.search import fuzzy_search, LevelKey
from helpers.models.sonolus.response import ServerItemList

router = APIRouter()


@router.get("", response_model=ServerItemList)
async def main(
    request: SonolusRequest,
    page: int = 0,
    keywords: str = "",
    difficulty: str = "all",
    minrating: int = 0,
    maxrating: int = 99,
    sort: str = "published_at",
    order: str = "desc",
    type: str = "quick",
    random: int = 0,
    artists: str = "",
    category: str = "",
):

    api = request.app.api
    source = request.app.base_url
    locale = request.state.loc
    localization = request.state.localization
    items_per_page = request.app.get_items_per_page("levels")

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
    vocal_map = {(m.id, v.id): v for m in musics for v in m.vocals}
    diff_map = {(m.id, d.difficulty): d for m in musics for d in m.difficulties}

    if keywords.strip():
        matched_keys = fuzzy_search(keywords)
        all_keys: list[LevelKey] = []
        seen = set()
        for lk in matched_keys:
            mid, vid, dname = lk
            if (
                mid in music_map
                and (mid, vid) in vocal_map
                and (mid, dname) in diff_map
            ):
                if lk not in seen:
                    seen.add(lk)
                    all_keys.append(lk)
    else:
        all_keys = [
            (m.id, v.id, d.difficulty)
            for m in musics
            for v in m.vocals
            for d in m.difficulties
        ]

    if difficulty != "all":
        all_keys = [k for k in all_keys if k[2] == difficulty]

    all_keys = [
        k
        for k in all_keys
        if (mid_diff := diff_map.get((k[0], k[2])))
        and minrating <= mid_diff.play_level <= maxrating
    ]

    if artists:
        included_artists = {a.strip().lower() for a in artists.split(",") if a.strip()}
        if included_artists:
            filtered = []
            for k in all_keys:
                vocal = vocal_map.get((k[0], k[1]))
                if vocal:
                    music = music_map[k[0]]
                    from helpers.models.api.music import get_vocal_artist

                    artist_name = get_vocal_artist(vocal, music).lower()
                    if any(a in artist_name for a in included_artists):
                        filtered.append(k)
            all_keys = filtered

    if category:
        included_cats = {c.strip().lower() for c in category.split(",") if c.strip()}
        if included_cats:
            all_keys = [
                k
                for k in all_keys
                if (v := vocal_map.get((k[0], k[1])))
                and v.caption.lower() in included_cats
            ]

    if random:
        rand_module.shuffle(all_keys)
        all_keys = all_keys[:items_per_page]
        total = len(all_keys)
        page_count = 1
        page = 0
    else:
        if sort == "rating":
            all_keys.sort(
                key=lambda k: diff_map[(k[0], k[2])].play_level,
                reverse=(order == "desc"),
            )
        elif sort == "title":
            from helpers.level_builder import get_display_title

            all_keys.sort(
                key=lambda k: get_display_title(k[0], music_data, localization).lower(),
                reverse=(order == "desc"),
            )
        elif not keywords.strip():
            all_keys.sort(
                key=lambda k: music_map[k[0]].published_at,
                reverse=(order == "desc"),
            )

        total = len(all_keys)
        page_count = max(1, math.ceil(total / items_per_page))
        start = page * items_per_page
        all_keys = all_keys[start : start + items_per_page]

    items = []
    for mid, vid, dname in all_keys:
        music = music_map[mid]
        vocal = vocal_map[(mid, vid)]
        diff = diff_map[(mid, dname)]
        level = build_level_item(
            music=music,
            vocal=vocal,
            difficulty_name=dname,
            play_level=diff.play_level,
            engine=engine,
            source=source,
            localization=localization,
            music_data=music_data,
            levelbg=request.state.levelbg,
            spoiler_tag=locale.spoiler,
        )
        items.append(level)

    result = ServerItemList(pageCount=page_count, items=items)
    return result
