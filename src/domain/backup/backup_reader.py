from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, select

from domain.db.tables import AgentRunTable, PromptVersionTable, RunAgentConfigTable, RunTable
from models.backup import TableExport


_TABLES: list[type[SQLModel]] = [RunTable, AgentRunTable, RunAgentConfigTable, PromptVersionTable]


def read_tables(engine: Engine) -> list[TableExport]:
    exports: list[TableExport] = []
    with Session(engine) as session:
        for table in _TABLES:
            scalar_columns, json_columns = _classify_columns(table)
            rows = [row.model_dump() for row in session.exec(select(table)).all()]
            exports.append(TableExport(
                table_name=table.__tablename__,
                primary_key=_primary_key(table),
                scalar_columns=scalar_columns,
                json_columns=json_columns,
                rows=rows,
            ))
    return exports


def _classify_columns(table: type[SQLModel]) -> tuple[list[str], list[str]]:
    scalar, json_cols = [], []
    for column in table.__table__.columns:
        if isinstance(column.type, JSON):
            json_cols.append(column.name)
        else:
            scalar.append(column.name)
    return scalar, json_cols


def _primary_key(table: type[SQLModel]) -> str:
    return table.__table__.primary_key.columns.keys()[0]
