import json


class Loc:
    def __init__(self, data: dict, default: dict):
        self._data = data
        self._default = default

    def _get(self, value: str) -> str:
        try:
            return self._data[value]
        except KeyError:
            return self._default[value]

    def invalid_page_plural(self, page: int, max_page: int) -> str:
        return self._get("invalid_page_plural").format(
            page=f"{page:,}", max_page=f"{max_page:,}"
        )

    def invalid_page_singular(self, page: int, max_page: int) -> str:
        return self._get("invalid_page_singular").format(
            page=f"{page:,}", max_page=f"{max_page:,}"
        )

    @property
    def server_description(self) -> str:
        return self._get("server_description")

    @property
    def not_found(self) -> str:
        return self._get("not_found")

    @property
    def unknown_error(self) -> str:
        return self._get("unknown_error")

    @property
    def show_spoiler_charts(self) -> str:
        return self._get("show_spoiler_charts")

    @property
    def show_spoiler_charts_desc(self) -> str:
        return self._get("show_spoiler_charts_desc")

    def item_not_found(self, item: str, name: str) -> str:
        return self._get("item_not_found").format(item=item, name=name)

    def items_not_found(self, item: str) -> str:
        return self._get("items_not_found").format(item=item)

    @property
    def spoiler(self) -> str:
        return self._get("spoiler")

    @property
    def data_loading(self) -> str:
        return self._get("data_loading")

    def other_section_title(self, vocals: int, difficulties: int) -> str:
        if vocals and difficulties:
            v = "1v" if vocals == 1 else "nv"
            d = "1d" if difficulties == 1 else "nd"
            return self._get(f"other_{v}_{d}").format(
                vocals=vocals, difficulties=difficulties
            )
        elif vocals:
            key = "other_1v" if vocals == 1 else "other_nv"
            return self._get(key).format(vocals=vocals)
        else:
            key = "other_1d" if difficulties == 1 else "other_nd"
            return self._get(key).format(difficulties=difficulties)


class LocaleManager:
    def __init__(self, default_locale: str):
        self.default_locale = default_locale
        self.locales: dict[str, Loc] = {}

        self._default_locale = None
        self._default_locale = self.load_locale("en", overwrite_default={})

    def load_locale(self, locale: str, overwrite_default: dict = None) -> Loc:
        if locale == "zhs":
            locale = "zh-cn"
        elif locale == "zht":
            locale = "zh-TW"
        if locale in self.locales:
            return self.locales[locale]
        try:
            with open(f"locales/locales/{locale}.json", "r", encoding="utf8") as f:
                d = json.load(f)
            locale_class = Loc(
                d,
                (
                    overwrite_default
                    if overwrite_default is not None
                    else self._default_locale._data
                ),
            )
            self.locales[locale] = locale_class
            return locale_class
        except FileNotFoundError:
            return self._default_locale

    def assert_supported(self, locale: str):
        supported = [
            "el",
            "en",
            "es",
            "fr",
            "id",
            "it",
            "ja",
            "ko",
            "ru",
            "tr",
            "pt",
            "zh-cn",
            "zh-TW",
            "vi",
            "tl",
        ]
        if locale not in supported:
            raise AssertionError(f"Locale '{locale}' is not supported.")

    def get_messages(self, locale: str) -> tuple[Loc, str]:
        if locale == "zhs":
            locale = "zh-cn"
        elif locale == "zht":
            locale = "zh-TW"
        try:
            self.assert_supported(locale)
        except AssertionError:
            locale = "en"
        locale_class = self.load_locale(locale)
        return locale_class, locale


Locale = LocaleManager(default_locale="en")
