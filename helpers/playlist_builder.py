from helpers.models.api.music import (
    Music,
    translate_caption,
)
from helpers.models.sonolus.item import PlaylistItem, LevelItem
from helpers.models.sonolus.misc import SRL, Tag
from helpers.level_builder import (
    build_level_item,
    get_display_title,
)


def make_playlist_id(music_id: int) -> str:
    return f"sss-{music_id}"


def parse_playlist_id(playlist_id: str) -> int | None:
    parts = playlist_id.split("-")
    if len(parts) != 2 or parts[0] != "sss":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def build_playlist_description(
    music: Music,
    music_data: dict[str, list[Music]] | None = None,
) -> str:
    from helpers.level_builder import _get_all_title_variants

    lines = []
    if music.lyricist:
        lines.append(f"#LYRICIST:#SEPARATOR_COLON:{music.lyricist}")
    if music.composer:
        lines.append(f"#COMPOSER:#SEPARATOR_COLON:{music.composer}")
    if music.arranger:
        lines.append(f"#ARRANGER:#SEPARATOR_COLON:{music.arranger}")

    variants = _get_all_title_variants(music, music_data)
    if variants:
        lines.append("")
        lines.append(" ".join(variants))

    return "\n".join(lines)


async def build_playlist_item(
    music: Music,
    engine,
    source: str,
    localization: str = "en",
    music_data: dict[str, list[Music]] | None = None,
    levelbg: str = "v3",
) -> PlaylistItem:
    title = music.title
    if music_data:
        title = get_display_title(music.id, music_data, localization)

    seen = set()
    unique_tags = []
    for v in music.vocals:
        translated = translate_caption(v.caption, localization)
        if translated not in seen:
            seen.add(translated)
            unique_tags.append(Tag(title=translated))

    sorted_diffs = sorted(music.difficulties, key=lambda d: d.play_level, reverse=True)
    levels: list[LevelItem] = []
    for vocal in music.vocals:
        for diff in sorted_diffs:
            level = build_level_item(
                music=music,
                vocal=vocal,
                difficulty_name=diff.difficulty,
                play_level=diff.play_level,
                engine=engine,
                source=source,
                localization=localization,
                music_data=music_data,
                levelbg=levelbg,
            )
            levels.append(level)

    cover_url = music.jacket_url or ""

    return PlaylistItem(
        name=make_playlist_id(music.id),
        source=source,
        title=title,
        subtitle=f"{len(music.vocals)} version{'s' if len(music.vocals) != 1 else ''}, {len(music.difficulties)} difficult{'ies' if len(music.difficulties) != 1 else 'y'}",
        author=(
            "HATSUNE MIKU: COLORFUL STAGE!"
            if localization == "en"
            else "プロジェクトセカイ カラフルステージ！ feat. 初音ミク"
        ),
        tags=unique_tags,
        levels=levels,
        thumbnail=SRL(url=cover_url),
    )
