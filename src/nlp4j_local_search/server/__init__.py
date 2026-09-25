from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import create_app
    from .service import ServerConfig


def __getattr__(name: str):
    if name == "create_app":
        from .app import create_app as _create_app
        return _create_app
    if name == "ServerConfig":
        from .service import ServerConfig as _ServerConfig
        return _ServerConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_app",
    "ServerConfig",
]
