from fastapi import APIRouter
from fastapi import HTTPException, status

from core import SonolusRequest
from helpers.data_compilers import (
    compile_engines_list,
    compile_backgrounds_list,
    compile_effects_list,
    compile_particles_list,
    compile_skins_list,
)
from helpers.level_builder import fetch_music_data, get_merged_musics, get_display_title
from helpers.models.sonolus.item import BackgroundItem, ServerItem
from helpers.models.sonolus.misc import SRL
from helpers.sonolus_typings import ItemType
from helpers.models.sonolus.response import ServerItemDetails

router = APIRouter()


@router.get("", response_model=ServerItemDetails)
async def main(request: SonolusRequest, item_type: ItemType, item_name: str):
    locale = request.state.loc
    source = request.app.base_url
    item_data: ServerItem | None = None

    match item_type:
        case "engines":
            data = [
                item.to_engine_item()
                for item in await request.app.run_blocking(
                    compile_engines_list, source, request.state.localization
                )
            ]
        case "skins":
            data = [
                item.to_skin_item()
                for item in await request.app.run_blocking(compile_skins_list, source)
            ]
        case "backgrounds":
            data = await request.app.run_blocking(compile_backgrounds_list, source)
            # handle dynamic per-song backgrounds
            if item_name.startswith("sss-bg-") and not any(
                b.name == item_name for b in data
            ):
                parts = item_name.removeprefix("sss-bg-").rsplit("-", 1)
                if len(parts) == 2:
                    music_vocal_str, bg_version = parts[0], parts[1]
                    mv_parts = music_vocal_str.rsplit("-", 1)
                    if len(mv_parts) == 2:
                        try:
                            music_id, vocal_id = int(mv_parts[0]), int(mv_parts[1])
                        except ValueError:
                            pass
                        else:
                            music_data = await fetch_music_data(request.app.api)
                            musics = get_merged_musics(
                                music_data,
                                request.state.show_spoilers,
                                request.state.localization,
                            )
                            music = next((m for m in musics if m.id == music_id), None)
                            if music:
                                vocal = next(
                                    (v for v in music.vocals if v.id == vocal_id), None
                                )
                                jacket_variant = next(
                                    (
                                        v
                                        for v in (vocal.variants if vocal else [])
                                        if v.asset_type == "jacket"
                                    ),
                                    None,
                                )
                                if bg_version == "v3":
                                    bg_url = (
                                        jacket_variant.background_v3_url
                                        if jacket_variant
                                        and jacket_variant.background_v3_url
                                        else music.background_v3_url
                                    )
                                else:
                                    bg_url = (
                                        jacket_variant.background_v1_url
                                        if jacket_variant
                                        and jacket_variant.background_v1_url
                                        else music.background_v1_url
                                    )
                                cover_url = (
                                    jacket_variant.jacket_url
                                    if jacket_variant and jacket_variant.jacket_url
                                    else music.jacket_url
                                )
                                all_bgs = await request.app.run_blocking(
                                    compile_backgrounds_list, source, True
                                )
                                template_bg = next(
                                    (b for b in all_bgs if b.name == "pjsk_template"),
                                    None,
                                )
                                if template_bg and bg_url:
                                    item_data = BackgroundItem(
                                        name=item_name,
                                        source=source,
                                        title=f"PJSK {bg_version.upper()}",
                                        subtitle=get_display_title(
                                            music.id,
                                            music_data,
                                            request.state.localization,
                                        ),
                                        author="",
                                        tags=[],
                                        thumbnail=SRL(url=cover_url),
                                        data=template_bg.data,
                                        image=SRL(url=bg_url),
                                        configuration=template_bg.configuration,
                                    )
        case "effects":
            data = await request.app.run_blocking(compile_effects_list, source)
        case "particles":
            data = await request.app.run_blocking(compile_particles_list, source)
        case _:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=locale.item_not_found(item_type, item_name),
            )

    if not item_data:
        item_data = next((i for i in data if i.name == item_name), None)
        if not item_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=locale.item_not_found(
                    item_type.capitalize().removesuffix("s"), item_name
                ),
            )

    return ServerItemDetails(
        item=item_data,
        description=(
            item_data.description
            if hasattr(item_data, "description") and item_data.description
            else None
        ),
        actions=[],
        hasCommunity=False,
        leaderboards=[],
        sections=[],
    )
