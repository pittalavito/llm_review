import csv
import io
import json
import zipfile

from models.backup import TableExport

def create_manifest(timestamp, app_version) -> dict:
    return {
        "created_at": timestamp.isoformat(),
        "app_version": app_version,
        "tables": {}
    }

def write_table(archive: zipfile.ZipFile, export: TableExport) -> None:
    archive.writestr(f"{export.table_name}/{export.table_name}.csv", _to_csv(export))
    if not export.json_columns:
        return
    
    for row in export.rows:
        key = _safe_name(row.get(export.primary_key))
        payload = {col: row.get(col) for col in export.json_columns}
        archive.writestr(f"{export.table_name}/{key}.json", _to_json(payload))
      
def write_manifest(archive: zipfile.ZipFile, manifest: dict) -> None:
    archive.writestr("manifest.json", _to_json(manifest))
  

def _to_csv(export: TableExport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=export.scalar_columns,
        extrasaction="ignore",
        restval="",
    )
    writer.writeheader()
    for row in export.rows:
        writer.writerow({col: _csv_cell(row.get(col)) for col in export.scalar_columns})
    return output.getvalue()


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _to_json(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _safe_name(value) -> str:
    """Filesystem-safe primary key for a JSON filename."""
    text = str(value)
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text)