"""
Example demonstrating ConfigModel usage in PICLE shells.

This example shows how to create a configuration management system using
ConfigModel to handle YAML configuration files with structured validation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from picle.models import ConfigModel, PipeFunctionsModel
from picle.picle import App

# --------------------------------------------------------------------------------
# Configuration Structure Models
# --------------------------------------------------------------------------------


class SeverityEnum(str, Enum):
    """Logging severity levels."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class TerminalLoggingConfig(BaseModel):
    """Terminal logging configuration."""

    severity: SeverityEnum = Field(
        SeverityEnum.info, description="Logging severity level"
    )
    format: str = Field(None, description="Log message format", alias="format")


class FileLoggingConfig(BaseModel):
    """File logging configuration."""

    enabled: bool = Field(False, description="Enable file logging")
    path: str = Field(None, description="Log file path")
    severity: SeverityEnum = Field(
        SeverityEnum.warning, description="File logging severity level"
    )


class LoggingConfigModel(BaseModel):
    """Main logging configuration."""

    terminal: TerminalLoggingConfig = Field(
        None, description="Terminal logging configuration"
    )
    file: FileLoggingConfig = Field(None, description="File logging configuration")


# --------------------------------------------------------------------------------
# Configuration Store with Commands
# --------------------------------------------------------------------------------


class MyConfigStore(ConfigModel):
    """
    Configuration store for application settings.

    This model manages YAML configuration files and provides commands
    to view, get, and set configuration values.
    """

    # Configuration structure definition
    logging: LoggingConfigModel = Field(None, description="Logging configuration")

    class PicleConfig:
        subshell = True
        prompt = "test-config-shell[cfg]#"
        config_file = "app_config.yaml"  # Default config file path


# --------------------------------------------------------------------------------
# Root Shell Model
# --------------------------------------------------------------------------------


class RootShell(BaseModel):
    """Root shell with config command."""

    configure_terminal: MyConfigStore = Field(
        None, description="Configuration management commands"
    )

    class PicleConfig:
        pipe = PipeFunctionsModel
        prompt = "test-config-shell#"


# --------------------------------------------------------------------------------
# Example Usage
# --------------------------------------------------------------------------------


if __name__ == "__main__":
    shell = App(RootShell)
    shell.start()
