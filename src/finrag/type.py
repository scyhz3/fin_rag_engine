"""Define the companies included in the EDINET download scope."""


COMPANIES = {
    "E00776": "信越化学工業株式会社",
    "E02778": "ソフトバンクグループ株式会社",
    "E02126": "三菱重工業株式会社",
    "E02655": "株式会社サンリオ",
    "E02497": "伊藤忠商事株式会社",
}

DOCUMENT_TYPES = {
    "120": "annual_securities_report",
    "130": "annual_securities_report",
}

DEI_FIELDS = {
    "CurrentFiscalYearStartDateDEI",
    "CurrentFiscalYearEndDateDEI",
    "EDINETCodeDEI",
    "FilerNameInJapaneseDEI",
}
