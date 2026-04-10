#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/agent.py
XWChatAgent implementation.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.4
Generation Date: 07-Jan-2025
"""

from __future__ import annotations
from typing import Any
from pathlib import Path
from exonware.xwsystem import get_logger
from .base import AChatAgent
from .contracts import IChatProvider
from .errors import XWChatAgentError
logger = get_logger(__name__)
# xwstorage and xwauth are imported lazily in _init_google_storage and _init_google_auth
# to avoid pulling in heavy dependency chains (and their deprecation warnings) when not using Google Storage.


class XWChatAgent(AChatAgent):
    """Concrete implementation of chat agent."""

    def __init__(
        self,
        name: str,
        title: str = "",
        description: str = "",
        data_path: str | None = None,
        storage_connection: Any | None = None,
        use_google_storage: bool = False,
        google_storage_config: dict[str, Any] | None = None,
        **kwargs
    ):
        """
        Initialize chat agent.
        Args:
            name: Agent name (used as agent_id for data storage)
            title: Agent title
            description: Agent description
            data_path: Optional base path for data storage (defaults to xwchat/data/xwchat)
            storage_connection: Optional xwstorage connection for remote storage (GCS, etc.)
            use_google_storage: Whether to use Google Cloud Storage for data persistence
            google_storage_config: Optional Google Storage configuration:
                - bucket: GCS bucket name (required)
                - project: GCP project ID (optional)
                - credentials_path: Path to service account credentials (optional)
                - credentials_dict: Service account credentials dict (optional)
            **kwargs: Additional agent metadata
        """
        self._name = name
        self._title = title or name
        self._description = description
        self._metadata = kwargs
        self._providers: dict[str, IChatProvider] = {}
        # Set up data path
        if data_path:
            self._data_path = Path(data_path)
        else:
            # Default: xwchat/.data/xwchat
            current_file = Path(__file__).resolve()
            # Go up from: xwchat/src/exonware/xwchat/agent.py
            # To: xwchat/
            xwchat_root = current_file.parent.parent.parent.parent
            self._data_path = xwchat_root / ".data" / "xwchat"
        self._data_path = Path(self._data_path)
        # Set up storage connection
        self._storage_connection: Any | None = storage_connection
        self._use_google_storage = use_google_storage
        # Initialize Google Storage connection if requested
        if use_google_storage and not self._storage_connection:
            if google_storage_config:
                self._init_google_storage(google_storage_config)
        # Set up xwauth for Google OAuth (if using Google Storage)
        self._auth: Any | None = None
        if use_google_storage:
            self._init_google_auth()
    @property

    def agent_id(self) -> str:
        """Get agent ID (same as name)."""
        return self._name
    @property

    def data_path(self) -> Path:
        """Get base data path for this agent."""
        return self._data_path
    @property

    def storage_connection(self) -> Any | None:
        """Get storage connection (xwstorage connection)."""
        return self._storage_connection
    @property

    def auth(self) -> Any | None:
        """Get authentication instance (xwauth)."""
        return self._auth

    def _init_google_storage(self, config: dict[str, Any]) -> None:
        """Initialize Google Cloud Storage connection."""
        try:
            from exonware.xwstorage import XWConnection, XWStorage
        except ImportError:
            logger.warning("xwstorage not available. Install with: pip install exonware-xwstorage")
            return
        try:
            bucket = config.get("bucket")
            if not bucket:
                raise ValueError("Google Storage config must include 'bucket'")
            # Build xwstorage config
            storage_config = {
                "connector": "gcs",
                "bucket": bucket,
                "format": "json",
            }
            # Add optional config
            if "project" in config:
                storage_config["project"] = config["project"]
            if "credentials_path" in config:
                storage_config["credentials_path"] = config["credentials_path"]
            if "credentials_dict" in config:
                storage_config["credentials_dict"] = config["credentials_dict"]
            # Create xwstorage connection
            # Use auth if available (from xwauth)
            auth_for_storage = self._auth if self._auth else None
            self._storage_connection = XWConnection(
                auth=auth_for_storage,
                config=storage_config,
                connection_id=f"xwchat_{self._agent_id}_gcs"
            )
            logger.info(f"Initialized Google Storage connection: bucket={bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Storage: {e}", exc_info=True)
            self._storage_connection = None

    def _init_google_auth(self) -> None:
        """Initialize Google OAuth authentication using xwauth."""
        try:
            from exonware.xwauth import XWAuth
            from exonware.xwstorage import XWConnection
        except ImportError:
            logger.warning("xwauth/xwstorage not available, cannot initialize Google OAuth")
            return
        try:
            # Set up auth data path in data/ folder
            auth_data_path = self._data_path / "auth" / "google"
            auth_data_path.mkdir(parents=True, exist_ok=True)
            # Create local storage for auth data (when xwstorage is available)
            auth_storage_config = {
                "connector": "local",
                "format": "json",
                "address": str(auth_data_path / "auth_data.json")
            }
            auth_storage = XWConnection(
                auth=None,
                config=auth_storage_config,
                connection_id=f"xwchat_{self._agent_id}_auth_storage"
            )
            # Initialize xwauth with Google provider
            # Note: Client ID and secret should be provided via environment or config
            # For now, we'll create auth instance that can be configured later
            self._auth = XWAuth(
                storage=auth_storage,
                jwt_secret="xwchat-secret",  # Should be configurable
                providers=["google"]  # Enable Google OAuth provider
            )
            logger.info(f"Initialized Google OAuth authentication (data path: {auth_data_path})")
        except Exception as e:
            logger.error(f"Failed to initialize Google OAuth: {e}", exc_info=True)
            self._auth = None
    @property

    def name(self) -> str:
        """Get agent name."""
        return self._name
    @property

    def title(self) -> str:
        """Get agent title."""
        return self._title
    @property

    def description(self) -> str:
        """Get agent description."""
        return self._description
    @property

    def metadata(self) -> dict[str, Any]:
        """Get agent metadata."""
        return self._metadata.copy()

    def add_provider(self, provider: IChatProvider) -> None:
        """Add a chat provider."""
        if not isinstance(provider, IChatProvider):
            raise XWChatAgentError(f"Provider must implement IChatProvider interface")
        # Pass agent_id and data_path to provider if it supports it
        if hasattr(provider, '_agent_id') and hasattr(provider, '_data_path'):
            # Provider will use these if not already set
            if not hasattr(provider, '_agent_id_set') or not provider._agent_id_set:
                provider._agent_id = self._agent_id
                provider._data_path = self._data_path
                provider._agent_id_set = True
        # Pass storage connection to provider if it supports it
        if hasattr(provider, '_storage_connection') and self._storage_connection:
            provider._storage_connection = self._storage_connection
            provider._use_remote_storage = True
        provider_name = provider.provider_name
        if provider_name in self._providers:
            logger.warning(f"Provider '{provider_name}' already exists, replacing it")
        self._providers[provider_name] = provider
        logger.info(f"Added provider '{provider_name}' to agent '{self._name}'")

    def providers(self, *providers: IChatProvider) -> XWChatAgent:
        """
        Add one or more providers (fluent interface).
        Args:
            *providers: One or more chat providers to add
        Returns:
            Self for method chaining
        """
        for provider in providers:
            self.add_provider(provider)
        return self

    def remove_provider(self, provider_name: str) -> None:
        """Remove a chat provider."""
        if provider_name not in self._providers:
            logger.warning(f"Provider '{provider_name}' not found")
            return
        del self._providers[provider_name]
        logger.info(f"Removed provider '{provider_name}' from agent '{self._name}'")

    def get_provider(self, provider_name: str) -> IChatProvider | None:
        """Get provider by name."""
        return self._providers.get(provider_name)

    def list_providers(self) -> list[str]:
        """List all provider names."""
        return list(self._providers.keys())

    def __getitem__(self, provider_name: str) -> IChatProvider:
        """Get provider using dictionary-like access."""
        provider = self.get_provider(provider_name)
        if provider is None:
            raise XWChatAgentError(f"Provider '{provider_name}' not found")
        return provider

    def __contains__(self, provider_name: str) -> bool:
        """Check if provider exists."""
        return provider_name in self._providers

    def __len__(self) -> int:
        """Get number of providers."""
        return len(self._providers)

    def __repr__(self) -> str:
        """String representation."""
        return f"XWChatAgent(name='{self._name}', title='{self._title}', providers={len(self._providers)})"
