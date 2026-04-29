"""Host cluster for provisioning validation environments (vclusters, etc.).

Multiple rows supported from day 1. Admins configure one or more host clusters
via the Settings page. Each stores:
  - an encrypted kubeconfig used by Foyre to talk to the host;
  - defaults applied to newly-created validation environments;
  - the result of the most recent connection test.

The kubeconfig is *never* returned in API responses; it's write-only from the
API surface.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HostClusterConfig(Base):
    __tablename__ = "host_cluster_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="vcluster")

    # Fernet-encrypted kubeconfig (bytes). Decrypted in-memory when needed.
    kubeconfig_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    # Optional context override; null means use kubeconfig's current-context.
    context_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # External hostname / IP that validation-env NodePort services should be
    # reachable at. Null => fall back to the host's node InternalIP at
    # provisioning time.
    external_node_host: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Defaults applied to new validation clusters created against this host.
    ttl_hours: Mapped[int] = mapped_column(Integer, default=72)
    cpu_quota: Mapped[str] = mapped_column(String(32), default="4")
    memory_quota: Mapped[str] = mapped_column(String(32), default="8Gi")
    storage_quota: Mapped[str] = mapped_column(String(32), default="10Gi")

    apply_default_network_policy: Mapped[bool] = mapped_column(Boolean, default=True)
    apply_default_resource_quota: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_regenerate_kubeconfig: Mapped[bool] = mapped_column(Boolean, default=True)

    # Result of the most recent connection test.
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_test_status: Mapped[str] = mapped_column(
        String(32), default="untested", server_default="untested"
    )  # untested | connected | failed
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_test_cluster_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_test_node_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_test_has_storage_class: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
