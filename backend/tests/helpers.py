import openpyxl

DEFAULT_COLUMNS = [
    "item_type",
    "japanese",
    "kana",
    "romaji",
    "meanings",
    "part_of_speech",
    "example_japanese",
    "example_kana",
    "example_english",
    "similar_items",
    "source_note",
]


def write_wordbank(path, rows, columns=None, sheet_name="items"):
    columns = columns or DEFAULT_COLUMNS
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(columns)
    for row in rows:
        worksheet.append([row.get(col, "") for col in columns])
    workbook.save(path)
