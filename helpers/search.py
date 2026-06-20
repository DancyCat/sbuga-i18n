import json
import os
import unicodedata
import re

import cutlet
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from helpers.models.api.music import (
    Music,
    _build_char_name,
)

_katsu_hepburn = cutlet.Cutlet(
    system="hepburn", use_foreign_spelling=False, ensure_ascii=False
)
_katsu_nihon = cutlet.Cutlet(
    system="nihon", use_foreign_spelling=False, ensure_ascii=False
)
_katsu_kunrei = cutlet.Cutlet(
    system="kunrei", use_foreign_spelling=False, ensure_ascii=False
)

ROMANIZERS = [
    lambda text: _katsu_hepburn.romaji(text).lower().strip(),
    lambda text: _katsu_nihon.romaji(text).lower().strip(),
    lambda text: _katsu_kunrei.romaji(text).lower().strip(),
]

CACHE_FILE = "cache/search_maps.json"


def preprocess(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()
    STAR_LIKE = (
        r"[\u2600-\u26FF"
        r"\U0001F300-\U0001F5FF"
        r"\U0001F600-\U0001F64F"
        r"\U0001F680-\U0001F6FF]"
    )
    text = re.sub(STAR_LIKE, " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _romanize(text: str) -> list[str]:
    keys = []
    for fn in ROMANIZERS:
        try:
            r = fn(text)
        except Exception:
            continue
        if r and r != preprocess(text):
            keys.append(preprocess(r))
    return list(dict.fromkeys(keys))


LevelKey = tuple[int, int, str]

_search_map: dict[str, set[LevelKey]] = {}
_vocal_id_map: dict[str, set[LevelKey]] = {}
_playlist_map: dict[str, set[int]] = {}
_all_artists: list[str] = []
_all_captions: list[str] = []
_min_level: int = 1
_max_level: int = 40
_cached_versions: dict[str, str] = {}


def _add_keys(keys: list[str], level_keys: list[LevelKey]):
    for key in keys:
        pk = preprocess(key)
        if pk:
            _search_map.setdefault(pk, set()).update(level_keys)


def _add_playlist_keys(keys: list[str], music_ids: list[int]):
    for key in keys:
        pk = preprocess(key)
        if pk:
            _playlist_map.setdefault(pk, set()).update(music_ids)


def _save_to_disk():
    os.makedirs("cache", exist_ok=True)
    serializable_map = {k: [list(lk) for lk in v] for k, v in _search_map.items()}
    serializable_playlist = {k: list(v) for k, v in _playlist_map.items()}
    data = {
        "versions": _cached_versions,
        "search_map": serializable_map,
        "vocal_id_map": {k: [list(lk) for lk in v] for k, v in _vocal_id_map.items()},
        "playlist_map": serializable_playlist,
        "all_artists": _all_artists,
        "all_captions": _all_captions,
        "min_level": _min_level,
        "max_level": _max_level,
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _load_from_disk() -> bool:
    global _search_map, _vocal_id_map, _playlist_map, _all_artists, _all_captions, _min_level, _max_level, _cached_versions
    if not os.path.exists(CACHE_FILE):
        return False
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cached_versions = data.get("versions", {})
        _search_map = {
            k: {tuple(lk) for lk in v} for k, v in data.get("search_map", {}).items()
        }
        _vocal_id_map = {
            k: {tuple(lk) for lk in v} for k, v in data.get("vocal_id_map", {}).items()
        }
        _playlist_map = {k: set(v) for k, v in data.get("playlist_map", {}).items()}
        _all_artists = data.get("all_artists", [])
        _all_captions = data.get("all_captions", [])
        _min_level = data.get("min_level", 1)
        _max_level = data.get("max_level", 40)
        return True
    except Exception as e:
        print(f"[SSS] Failed to load search cache: {e}")
        return False


def get_cached_versions() -> dict[str, str]:
    return _cached_versions


def needs_rebuild(versions: dict[str, str]) -> bool:
    if not _search_map:
        if _load_from_disk() and versions == _cached_versions:
            return False
        return True
    return versions != _cached_versions


def build_search_maps(
    musics: list[Music],
    music_data: dict[str, list[Music]],
    versions: dict[str, str] | None = None,
):
    global _all_artists, _all_captions, _min_level, _max_level, _cached_versions
    _search_map.clear()
    _vocal_id_map.clear()
    _playlist_map.clear()

    all_artists_set: set[str] = set()
    all_captions_set: set[str] = set()
    min_lv = 99
    max_lv = 0

    for music in musics:
        mid_list = [music.id]
        all_level_keys: list[LevelKey] = []
        for vocal in music.vocals:
            for diff in music.difficulties:
                all_level_keys.append((music.id, vocal.id, diff.difficulty))

        all_title_keys: list[str] = []
        for source_list in music_data.values():
            for m in source_list:
                if m.id == music.id:
                    all_title_keys.extend(m.title_variants)
        all_title_keys.extend(music.title_variants)
        all_title_keys.append(music.title)
        if music.pronunciation:
            all_title_keys.append(music.pronunciation)
        deduped_titles = list(dict.fromkeys(all_title_keys))
        _add_keys(deduped_titles, all_level_keys)
        _add_playlist_keys(deduped_titles, mid_list)

        _add_keys([str(music.id)], all_level_keys)
        _add_playlist_keys([str(music.id)], mid_list)

        if music.artist:
            artist_keys = [music.artist.name, *_romanize(music.artist.name)]
            if music.artist.pronunciation:
                artist_keys.append(music.artist.pronunciation)
                artist_keys.extend(_romanize(music.artist.pronunciation))
            _add_keys(artist_keys, all_level_keys)
            _add_playlist_keys(artist_keys, mid_list)

        for field in [music.lyricist, music.composer, music.arranger]:
            if field:
                field_keys = [field, *_romanize(field)]
                _add_keys(field_keys, all_level_keys)
                _add_playlist_keys(field_keys, mid_list)

        for vocal in music.vocals:
            vocal_level_keys = [
                (music.id, vocal.id, diff.difficulty) for diff in music.difficulties
            ]

            vocal_id_str = preprocess(str(vocal.id))
            _add_keys([vocal_id_str], vocal_level_keys)
            _vocal_id_map.setdefault(vocal_id_str, set()).update(vocal_level_keys)

            all_captions_set.add(vocal.caption)

            chars = sorted(vocal.characters, key=lambda c: c.seq)
            for c in chars:
                if c.character_type == "game_character":
                    char_data = music.game_characters.get(c.character_id)
                    if char_data:
                        name = _build_char_name(char_data)
                        all_artists_set.add(name)
                        name_keys = [name, *_romanize(name)]
                        if char_data.givenName:
                            name_keys.append(char_data.givenName)
                            name_keys.extend(_romanize(char_data.givenName))
                        if char_data.firstName:
                            name_keys.append(char_data.firstName)
                            name_keys.extend(_romanize(char_data.firstName))
                        _add_keys(name_keys, vocal_level_keys)
                else:
                    char_data = music.outside_characters.get(c.character_id)
                    if char_data:
                        all_artists_set.add(char_data.name)
                        name_keys = [char_data.name, *_romanize(char_data.name)]
                        _add_keys(name_keys, vocal_level_keys)

        for diff in music.difficulties:
            diff_level_keys = [
                (music.id, vocal.id, diff.difficulty) for vocal in music.vocals
            ]
            _add_keys([diff.difficulty], diff_level_keys)
            if diff.play_level < min_lv:
                min_lv = diff.play_level
            if diff.play_level > max_lv:
                max_lv = diff.play_level

    _all_artists = sorted(all_artists_set)
    _all_captions = sorted(all_captions_set)
    _min_level = min_lv if min_lv < 99 else 1
    _max_level = max_lv if max_lv > 0 else 40

    if versions:
        _cached_versions = versions

    if _search_map:
        _save_to_disk()
    print(f"[SSS] Search maps built: {len(_search_map)} keys")


def fuzzy_search(
    query: str, sensitivity: float = 0.65, limit: int = 200
) -> list[LevelKey]:
    if not _search_map or not query.strip():
        return []

    sensitivity_100 = sensitivity * 100
    query_pp = preprocess(query)

    scores: dict[LevelKey, float] = {}

    for key, level_keys in _search_map.items():
        similarity = fuzz.token_set_ratio(query_pp, key)
        edit_distance = Levenshtein.distance(query_pp, key)

        if edit_distance > 5:
            # only penalize character changes, not added/removed text
            excess = abs(len(key) - len(query_pp))
            real_edits = max(0, edit_distance - excess)
            excess_penalty = max(0, excess - 5) * 2
            edit_penalty = max(0, real_edits - 5) * 5
            similarity -= excess_penalty + edit_penalty

        if similarity >= sensitivity_100:
            vocal_lks = _vocal_id_map.get(key)
            for lk in level_keys:
                score = (
                    similarity * 0.9 if vocal_lks and lk in vocal_lks else similarity
                )
                if lk not in scores or score > scores[lk]:
                    scores[lk] = score

    sorted_keys = sorted(scores.keys(), key=lambda lk: scores[lk], reverse=True)
    return sorted_keys[:limit]


def fuzzy_search_playlists(
    query: str, sensitivity: float = 0.65, limit: int = 200
) -> list[int]:
    if not _playlist_map or not query.strip():
        return []

    sensitivity_100 = sensitivity * 100
    query_pp = preprocess(query)

    scores: dict[int, float] = {}

    for key, music_ids in _playlist_map.items():
        similarity = fuzz.token_set_ratio(query_pp, key)
        edit_distance = Levenshtein.distance(query_pp, key)

        if edit_distance > 5:
            excess = abs(len(key) - len(query_pp))
            real_edits = max(0, edit_distance - excess)
            excess_penalty = max(0, excess - 5) * 2
            edit_penalty = max(0, real_edits - 5) * 5
            similarity -= excess_penalty + edit_penalty

        if similarity >= sensitivity_100:
            for mid in music_ids:
                if mid not in scores or similarity > scores[mid]:
                    scores[mid] = similarity

    sorted_ids = sorted(scores.keys(), key=lambda mid: scores[mid], reverse=True)
    return sorted_ids[:limit]


def load_from_response(data: dict):
    global _search_map, _vocal_id_map, _playlist_map, _all_artists, _all_captions, _min_level, _max_level
    _search_map = {k: {tuple(lk) for lk in v} for k, v in data["search_map"].items()}
    _vocal_id_map = {
        k: {tuple(lk) for lk in v} for k, v in data.get("vocal_id_map", {}).items()
    }
    _playlist_map = {k: set(v) for k, v in data.get("playlist_map", {}).items()}
    _all_artists = data["all_artists"]
    _all_captions = data["all_captions"]
    _min_level = data["min_level"]
    _max_level = data["max_level"]


def get_all_artists() -> list[str]:
    return _all_artists


def get_all_captions() -> list[str]:
    return _all_captions


def get_level_range() -> tuple[int, int]:
    return _min_level, _max_level
