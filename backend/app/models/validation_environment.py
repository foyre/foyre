"""Validation environment: a real Kubernetes virtual cluster provisioned for a request.

One request can have many envs over its lifetime (create → tear down → create again).
The "current" env is the most recent non-torn-down row.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ValidationEnvironment(Base):
    __tablename__ = "validation_environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("intake_requests.id"), index=True
    )
    host_cluster_config_id: Mapped[int] = mapped_column(
        ForeignKey("host_cluster_configs.id")
    )

    # provisioning | ready | failed | torn_down
    status: Mapped[str] = mapped_column(
        String(32), default="provisioning", server_default="provisioning", index=True
    )

    # Kubernetes details
    namespace: Mapped[str] = mapped_column(String(200))
    vcluster_name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(32), default="vcluster")

    # Fernet-encrypted kubeconfig the requester downloads. Nullable until ready.
    user_kubeconfig_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # External endpoint we baked into the kubeconfig (for display).
    external_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extensions_used: Mapped[int] = mapped_column(Integer, default=0)

    # Last provisioning / teardown error, if any.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    torn_down_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    request = relationship("IntakeRequest")
