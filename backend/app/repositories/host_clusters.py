"""Thin DB access for host cluster configs."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.host_cluster_config import HostClusterConfig


def get(db: Session, id_: int) -> HostClusterConfig | None:
    return db.get(HostClusterConfig, id_)


def get_by_name(db: Session, name: str) -> HostClusterConfig | None:
    return db.execute(
        select(HostClusterConfig).where(HostClusterConfig.name == name)
    ).scalar_one_or_none()


def list_all(db: Session) -> list[HostClusterConfig]:
    stmt = select(HostClusterConfig).order_by(HostClusterConfig.id.asc())
    return list(db.execute(stmt).scalars())


def save(db: Session, row: HostClusterConfig) -> HostClusterConfig:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: HostClusterConfig) -> None:
    db.delete(row)
    db.commit()


def clear_other_defaults(db: Session, keep_id: int | None) -> None:
    """Only one host cluster may be marked default at a time."""
    for row in list_all(db):
        if row.is_default and row.id != keep_id:
            row.is_default = False
            db.add(row)
    db.commit()
