"""
HTTP Session Manager with Connection Pooling

This module provides a centralized HTTP session manager with connection pooling
for efficient HTTP requests across all clients in the application.

Features:
- Connection pooling and reuse
- Configurable pool sizes and timeouts
- Per-host connection management
- Thread-safe session handling
- Automatic retry with exponential backoff
"""

import requests
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class HTTPSessionManager:
    """
    Centralized HTTP session manager with connection pooling.

    This class provides optimized HTTP sessions with:
    - Connection pooling for better performance
    - Automatic retries with exponential backoff
    - Configurable timeouts and pool sizes
    - Thread-safe access to sessions
    """

    def __init__(self):
        self._sessions: Dict[str, requests.Session] = {}
        self._lock = threading.Lock()

    def get_session(
        self,
        base_url: str,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: Optional[float] = None,
    ) -> requests.Session:
        """
        Get or create an optimized HTTP session for a specific base URL.

        Args:
            base_url: Base URL for the session (e.g., 'https://api.github.com')
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections in each pool
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Default timeout for requests

        Returns:
            Configured requests.Session with connection pooling
        """
        with self._lock:
            if base_url not in self._sessions:
                session = self._create_session(
                    pool_connections=pool_connections,
                    pool_maxsize=pool_maxsize,
                    max_retries=max_retries,
                    backoff_factor=backoff_factor,
                    timeout=timeout,
                )
                self._sessions[base_url] = session
                logger.debug(f"Created new HTTP session for {base_url}")

            return self._sessions[base_url]

    def _create_session(
        self,
        pool_connections: int,
        pool_maxsize: int,
        max_retries: int,
        backoff_factor: float,
        timeout: Optional[float],
    ) -> requests.Session:
        """
        Create a new HTTP session with optimized configuration.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections in each pool
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Default timeout for requests

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        )

        # Create HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
        )

        # Mount adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default timeout if provided
        if timeout:
            session.timeout = timeout

        return session

    def close_all_sessions(self):
        """Close all active sessions and clear the cache."""
        with self._lock:
            for base_url, session in self._sessions.items():
                session.close()
                logger.debug(f"Closed HTTP session for {base_url}")
            self._sessions.clear()

    def get_session_info(self) -> Dict[str, int]:
        """
        Get information about active sessions.

        Returns:
            Dictionary with session count and connection pool information
        """
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "session_urls": list(self._sessions.keys()),
            }


# Global session manager instance
_session_manager: Optional[HTTPSessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> HTTPSessionManager:
    """
    Get the global HTTP session manager instance (singleton pattern).

    Returns:
        HTTPSessionManager instance
    """
    global _session_manager
    with _manager_lock:
        if _session_manager is None:
            _session_manager = HTTPSessionManager()
            logger.debug("Initialized global HTTP session manager")
        return _session_manager


def get_http_session(
    base_url: str,
    pool_connections: int = 10,
    pool_maxsize: int = 20,
    max_retries: int = 3,
    timeout: Optional[float] = None,
) -> requests.Session:
    """
    Convenience function to get an optimized HTTP session.

    Args:
        base_url: Base URL for the session
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum number of connections in each pool
        max_retries: Maximum number of retry attempts
        timeout: Default timeout for requests

    Returns:
        Configured requests.Session with connection pooling

    Example:
        ```python
        from utils.http_session import get_http_session

        # Get a session for GitHub API
        session = get_http_session("https://api.github.com", timeout=30)
        response = session.post("/graphql", json={"query": "..."})
        ```
    """
    manager = get_session_manager()
    return manager.get_session(
        base_url=base_url,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        max_retries=max_retries,
        timeout=timeout,
    )


def close_all_http_sessions():
    """Close all HTTP sessions (useful for cleanup)."""
    global _session_manager
    with _manager_lock:
        if _session_manager:
            _session_manager.close_all_sessions()
            _session_manager = None
            logger.debug("Closed all HTTP sessions")
