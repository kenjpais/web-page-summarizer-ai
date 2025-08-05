"""
Centralized settings management file.
"""

import os
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Only load `.env` if not in CI
if os.getenv("GITHUB_ACTIONS") != "true":
    dotenv_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path)


class APISettings(BaseSettings):
    """External API configuration settings."""

    # GitHub API
    github_api_url: str = Field(
        default="https://api.github.com/graphql", alias="GITHUB_GRAPHQL_API_URL"
    )
    github_server: str = Field(default="https://github.com", alias="GITHUB_SERVER")
    github_token: str = Field(..., alias="GH_API_TOKEN")
    github_timeout: int = Field(default=30, alias="GITHUB_TIMEOUT")
    github_rate_limit: int = Field(default=100, alias="GITHUB_RATE_LIMIT")

    # JIRA API
    jira_server: str = Field(alias="JIRA_SERVER")
    jira_timeout: int = Field(default=30, alias="JIRA_TIMEOUT")
    jira_batch_size: int = Field(default=500, alias="JIRA_BATCH_SIZE")
    # jira_max_results: int = Field(default=200, alias="JIRA_MAX_RESULTS")

    # LLM Configuration
    llm_provider: str = Field(
        default="local", alias="LLM_PROVIDER"
    )  # "local" or "gemini"

    # Local LLM API (Ollama)
    llm_api_url: str = Field(
        default="http://localhost:11434/api/generate", alias="LLM_API_URL"
    )
    llm_model: str = Field(default="mistral", alias="LLM_MODEL")
    # llm_timeout: int = Field(default=120, alias="LLM_TIMEOUT")

    # Google Gemini API
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # LLM Input Limits
    max_input_tokens: int = Field(
        default=50000, alias="MAX_INPUT_TOKENS"
    )  # Conservative limit for chunking
    chunk_overlap: int = Field(
        default=1000, alias="CHUNK_OVERLAP"
    )  # Overlap between chunks
    chunk_size: int = Field(
        default=40000, alias="CHUNK_SIZE"
    )  # Target chunk size in tokens

    @field_validator("github_api_url", "jira_server", "llm_api_url")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        """Validate that URLs are properly formatted."""
        if not v:
            raise ValueError("URL cannot be empty")

        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {v}")

        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"URL must use http or https: {v}")

        return v

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """Validate GitHub token format."""
        if not v:
            raise ValueError("GitHub token is required")

        # GitHub tokens should start with specific prefixes
        valid_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError("Invalid GitHub token format")

        return v


class DirectorySettings(BaseSettings):
    """File system and directory configuration."""

    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    test_data_dir: Path = Field(
        default=Path("tests") / Path("mocks"), alias="TEST_DATA_DIR"
    )
    config_dir: Path = Field(default=Path("config"), alias="CONFIG_DIR")
    logs_dir: Path = Field(default=Path("logs"), alias="LOGS_DIR")

    # Ensure directories exist on startup
    create_dirs_on_startup: bool = Field(default=True, alias="CREATE_DIRS_ON_STARTUP")

    @field_validator(
        "data_dir", "test_data_dir", "config_dir", "logs_dir", mode="before"
    )
    @classmethod
    def convert_to_path(cls, v: Any) -> Path:
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def create_directories(self) -> "DirectorySettings":
        """Create directories if they don't exist."""
        if self.create_dirs_on_startup:
            for directory in [
                self.data_dir,
                self.test_data_dir,
                self.config_dir,
                self.logs_dir,
            ]:
                directory.mkdir(parents=True, exist_ok=True)
        return self


class ProcessingSettings(BaseSettings):
    """Data processing configuration."""

    sources: List[str] = Field(default=["JIRA", "GITHUB"], alias="SOURCES")
    summarize_enabled: bool = Field(default=True, alias="SUMMARIZE_ENABLED")
    filter_on: bool = Field(default=True, alias="FILTER_ON")
    debug: bool = Field(default=False, alias="DEBUG")

    # Batch processing settings
    github_batch_size: int = Field(default=300, alias="GITHUB_BATCH_SIZE")
    parallel_processing: bool = Field(default=False, alias="PARALLEL_PROCESSING")
    max_workers: int = Field(default=4, alias="MAX_WORKERS")

    # URL validation
    allowed_protocols: List[str] = Field(
        default=["http", "https"], alias="ALLOWED_PROTOCOLS"
    )

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, v: Any) -> List[str]:
        """Parse sources from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format for SOURCES: {v}")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: List[str]) -> List[str]:
        """Validate that sources are supported."""
        supported_sources = {"JIRA", "GITHUB"}
        invalid_sources = set(v) - supported_sources
        if invalid_sources:
            raise ValueError(f"Unsupported sources: {invalid_sources}")
        return v

    def get_sources_dict(self) -> Dict[str, str]:
        """
        Get a dictionary mapping source names to their server URLs.

        Returns:
            Dictionary with source names as keys and server URLs as values
        """
        # We need to access the parent AppSettings to get the API settings
        from config.settings import get_settings

        settings = get_settings()
        result = {}

        for src in self.sources:
            # Convert source name to lowercase for attribute lookup
            src_lower = src.lower()
            server_attr = f"{src_lower}_server"

            # Try to get the server URL from the API settings
            if hasattr(settings.api, server_attr):
                server_url = getattr(settings.api, server_attr)
                result[src] = server_url
            else:
                # Log warning if server not found
                import logging

                logging.warning(
                    f"No server URL found for source '{src}' (looking for '{server_attr}')"
                )

        return result


class SecuritySettings(BaseSettings):
    """Security-related configuration."""

    # Allowed domains for external requests
    allowed_domains: List[str] = Field(
        default=["github.com", "api.github.com", "issues.redhat.com", "localhost"],
        alias="ALLOWED_DOMAINS",
    )

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def parse_domains(cls, v: Any) -> List[str]:
        """Parse domains from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback to comma-separated
                return [d.strip() for d in v.split(",")]
        return v


class ConfigFileSettings(BaseSettings):
    """Configuration for loading JSON/text config files."""

    config_file_path: Path = Field(
        default=Path("config/filter.json"), alias="CONFIG_FILE_PATH"
    )

    # File paths
    jira_filter_file: str = "jira_filter.json"
    jira_filter_out_file: str = "jira_filter_out.json"
    github_filter_file: str = "github_filter.json"
    required_jira_fields_file: str = "required_jira_fields.json"
    required_github_fields_file: str = "required_github_fields.json"

    # Template files
    summarize_prompt_template: str = "summarize_prompt_template.txt"
    example_summary_file: str = "example_summary.txt"
    classify_prompt_template: str = "classify_prompt_template.txt"
    project_summary_template: str = "summarize_project_prompt_template.txt"
    summarize_enabled_feature_gate_prompt_template: str = (
        "summarize_enabled_feature_gate_prompt_template.txt"
    )
    summarize_single_feature_gate_prompt_template: str = (
        "summarize_single_feature_gate_prompt_template.txt"
    )


class AppSettings(BaseSettings):
    """Main application settings that combines all other settings."""

    model_config = SettingsConfigDict(
        env_file=None, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_name: str = Field(default="release-page-summarizer", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")

    # Sub-settings (automatically initialized by Pydantic)
    api: APISettings = Field(default_factory=APISettings)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    config_files: ConfigFileSettings = Field(default_factory=ConfigFileSettings)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of: {valid_envs}")
        return v

    def is_production(self) -> bool:
        return self.environment == "production"

    def is_development(self) -> bool:
        return self.environment == "development"


# Configuration file loaders
class ConfigLoader:
    """Loads and caches configuration files."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._cache: Dict[str, Any] = {}

    @lru_cache(maxsize=32)
    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load and cache JSON configuration file."""
        file_path = self.settings.directories.config_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")

    @lru_cache(maxsize=32)
    def load_text_config(self, filename: str) -> str:
        """Load and cache text configuration file."""
        file_path = self.settings.directories.config_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode {file_path}: {e}")

    def get_jira_filter(self) -> Dict[str, Any]:
        """Get JIRA filter configuration."""
        return self.load_json_config(self.settings.config_files.jira_filter_file)

    def get_jira_filter_out(self) -> Dict[str, Any]:
        """Get JIRA filter-out configuration."""
        return self.load_json_config(self.settings.config_files.jira_filter_out_file)

    def get_required_jira_fields(self) -> List[str]:
        """Get required JIRA fields."""
        data = self.load_json_config(
            self.settings.config_files.required_jira_fields_file
        )
        return data if isinstance(data, list) else []

    def get_required_github_fields(self) -> List[str]:
        """Get required GitHub fields."""
        data = self.load_json_config(
            self.settings.config_files.required_github_fields_file
        )
        return data if isinstance(data, list) else []

    def get_summarize_prompt_template(self) -> str:
        """Get summarization prompt template."""
        return self.load_text_config(
            self.settings.config_files.summarize_prompt_template
        )

    def get_feature_gate_summarize_prompt_template(self) -> str:
        """Get feature gate summarization prompt template."""
        return self.load_text_config(
            self.settings.config_files.summarize_enabled_feature_gate_prompt_template
        )

    def get_single_feature_gate_summarize_prompt_template(self) -> str:
        """Get single feature gate summarization prompt template."""
        return self.load_text_config(
            self.settings.config_files.summarize_single_feature_gate_prompt_template
        )

    def get_project_summary_template(self) -> str:
        """Get project summarization prompt template."""
        return self.load_text_config(
            self.settings.config_files.project_summary_template
        )

    def get_example_summary(self) -> str:
        """Get example summary text."""
        return self.load_text_config(self.settings.config_files.example_summary_file)


# Global settings instance
@lru_cache()
def get_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()


@lru_cache()
def get_config_loader() -> ConfigLoader:
    """Get cached configuration loader."""
    return ConfigLoader(get_settings())


# Export commonly used functions
__all__ = [
    "AppSettings",
    "ConfigLoader",
    "get_settings",
    "get_config_loader",
]
