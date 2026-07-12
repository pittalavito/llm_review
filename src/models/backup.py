from dataclasses import dataclass

@dataclass
class TableExport:
    """One table's rows, with columns split into scalar (CSV) and JSON (files)."""
    table_name: str
    primary_key: str
    scalar_columns: list[str]
    json_columns: list[str]
    rows: list[dict]