"""CRUD repository for versioned prompt templates.
The database is the source of truth for prompt texts at compile time.
Versions are immutable: create() adds rows, update_meta() may only touch
description and is_active. seed_defaults() registers the code-shipped
templates without ever overwriting existing rows.
"""

from __future__ import annotations

import logging

from datetime import datetime, timezone
from hashlib import sha256
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from domain.db.tables import PromptVersionTable

logger = logging.getLogger(__name__)

class PromptRepository:

    def __init__(self, engine: Engine):
        self._engine = engine

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list(self, agent_role: str | None = None, include_inactive: bool = False) -> list[PromptVersionTable]:
        statement = select(PromptVersionTable)
        
        if agent_role is not None:
            statement = statement.where(PromptVersionTable.agent_role == agent_role)
        if not include_inactive:
            statement = statement.where(PromptVersionTable.is_active == True)
        statement = statement.order_by(PromptVersionTable.agent_role, PromptVersionTable.version_label)
        
        with Session(self._engine) as session:
            return list(session.exec(statement).all())

    def get(self, version_id: int) -> PromptVersionTable:
        """Raises ValueError if not found."""
        
        with Session(self._engine) as session:
            row = session.get(PromptVersionTable, version_id)
            if row is None:
                raise ValueError(f"Prompt version not found: {version_id}")
            return row

    def get_by_role_label(self, agent_role: str, version_label: str, only_active: bool = True) -> PromptVersionTable:
        """Raises ValueError if not found (or inactive when only_active)."""
        
        statement = select(PromptVersionTable).where(PromptVersionTable.agent_role == agent_role, PromptVersionTable.version_label == version_label)
        
        with Session(self._engine) as session:
            row = session.exec(statement).first()
        if row is None or (only_active and not row.is_active):
            raise ValueError(f"Prompt version not available: {agent_role}/{version_label}")
        return row

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(self, agent_role: str, version_label: str, template: str, description: str | None = None) -> PromptVersionTable:
        """Register a new immutable version. Raises ValueError if
        (agent_role, version_label) already exists."""
       
        with Session(self._engine) as session:
            duplicate = session.exec(
                select(PromptVersionTable.id).where(PromptVersionTable.agent_role == agent_role, PromptVersionTable.version_label == version_label)
            ).first()
            
            if duplicate is not None:
                raise ValueError(f"Prompt version already exists: {agent_role}/{version_label}")
            
            row = PromptVersionTable(
                agent_role=agent_role,
                version_label=version_label,
                template=template,
                template_hash=sha256(template.encode("utf-8")).hexdigest(),
                description=description,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            
            session.add(row)
            session.commit()
            session.refresh(row)
        logger.info("Prompt version created: %s/%s", agent_role, version_label)
        return row

    def update_meta(self, version_id: int, description: str | None = None, is_active: bool | None = None) -> PromptVersionTable:
        """Update mutable metadata only — the template text never changes.
        Raises ValueError if not found."""
        
        with Session(self._engine) as session:
            row = session.get(PromptVersionTable, version_id)
            if row is None:
                raise ValueError(f"Prompt version not found: {version_id}")
            if description is not None:
                row.description = description
            if is_active is not None:
                row.is_active = is_active
                
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def seed_defaults(self, seeds: list[tuple[str, str, str, str]]) -> int:
        """Insert the code-shipped templates missing from the registry.
        Never overwrites existing rows. Returns the number inserted."""
        
        inserted = 0
        with Session(self._engine) as session:
            existing = {
                (row.agent_role, row.version_label)
                for row in session.exec(
                    select(PromptVersionTable.agent_role, PromptVersionTable.version_label)
                ).all()
            }
            now = datetime.now(timezone.utc).isoformat()
            for agent_role, version_label, template, description in seeds:
                if (agent_role, version_label) in existing:
                    continue
                session.add(PromptVersionTable(
                    agent_role=agent_role,
                    version_label=version_label,
                    template=template,
                    template_hash=sha256(template.encode("utf-8")).hexdigest(),
                    description=description,
                    created_at=now,
                ))
                inserted += 1
            session.commit()
        if inserted:
            logger.info("Prompt registry seeded: %d new version(s)", inserted)
        return inserted
