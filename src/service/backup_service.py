"""DB backup as an in-memory ZIP.

Layout (one subfolder per table): a CSV with the scalar/indexed columns and,
for tables that have JSON-payload columns, one JSON file per record named by
its primary key. A manifest.json records timestamp, app version and row
counts. Nothing is written server-side — the bytes are streamed to the
browser as a download.
"""
import csv
import io
import logging
import zipfile
from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from config import Config
from domain.backup.backup_reader import read_tables
from domain.backup.backup_writer import create_manifest,  write_table, write_manifest

logger = logging.getLogger(__name__)


class BackupService:

    def __init__(self, engine: Engine, config: Config):
        self.engine = engine
        self.config = config

    def build_zip(self) -> tuple[bytes, str]:
        """Build the backup archive in memory. Returns (zip_bytes, filename)."""
        
        timestamp = datetime.now(timezone.utc)
        filename = f"db-backup_{timestamp.strftime('%Y-%m-%dT%H-%M-%S')}.zip"

        exports = read_tables(self.engine)
        
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            manifest = create_manifest(timestamp, self.config.app_version)
            for export in exports:
                manifest["tables"][export.table_name] = len(export.rows)
                write_table(archive, export)
            
            write_manifest(archive, manifest)

        logger.info("DB backup built: %s (%d tables)", filename, len(exports))
        return buffer.getvalue(), filename

