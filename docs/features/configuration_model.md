# `ConfigModel` (configuration shells)

PICLE ships a helper base model for “configuration-mode” shells: `picle.models.ConfigModel`.
It implements a common workflow:

- Load configuration from YAML (optional dependency: `pyyaml`)
- Stage edits into a temporary file (`<config_file>.tmp`)
- Review staged changes (`show changes`) and commit them (`commit`)
- Keep rotating backups on commit (`.old1`, `.old2`, ...)
- Roll back by loading a backup into the temp file (`rollback <n>`) and then committing

## `ConfigModel.PicleConfig` keys

`ConfigModel` reads additional settings from the concrete model’s `PicleConfig`.
These keys are **only honored by `ConfigModel`** (the core `App` ignores them):

| Name | Meaning |
| --- | --- |
| `config_file` | Path to the YAML config file (default: `configuration.yaml`) |
| `backup_on_save` | How many `.oldN` backups to keep when committing (0 disables backups) |
| `commit_hook` | Optional callable invoked after a successful commit |

## Sample Config Model Shell

Below is example of how to use configuration model to construct interactive shell to manage YAML file content.

```
"""
Example demonstrating ConfigModel usage in PICLE shells.

This example shows how to create a configuration management system using
ConfigModel to handle YAML configuration files with structured validation.
"""

from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, StrictStr

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

class WorkerConfigModel(BaseModel):
    timeout: int = Field(None, description="Worker timeout in seconds")
    num_threads: int = Field(None, description="Number of worker threads")
    use_chache: bool = Field(None, description="Whether to use cache for worker results")


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
    workers: dict[StrictStr, WorkerConfigModel] = Field(
        None, description="Worker configurations", json_schema_extra={"pkey": "worker_name", "pkey_description": "Name of the worker"}
    )
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

```

Above app constructs shell with this commands tree:

```
test-config-shell#man tree configure_terminal

R - required field, M - supports multiline input, D - dynamic key

root
└── configure_terminal:    Configuration management commands
    ├── show:    Show commands
    │   ├── configuration:    Show running configuration content
    │   └── changes:    Show uncommitted changes diff between temp and running config
    ├── commit:    Commit pending config changes
    ├── rollback:    Rollback to a backup version
    ├── erase-configuration:    Erase running configuration
    ├── clear-changes:    Discard uncommitted changes
    ├── logging:    Logging configuration
    │   ├── terminal:    Terminal logging configuration
    │   │   ├── severity:    Logging severity level, default 'SeverityEnum.info'
    │   │   └── format:    Log message format
    │   └── file:    File logging configuration
    │       ├── enabled:    Enable file logging, default 'False'
    │       ├── path:    Log file path
    │       └── severity:    File logging severity level, default 'SeverityEnum.warning'
    └── workers:    Worker configurations
        ├── worker_name (D):    Name of the worker
        ├── timeout:    Worker timeout in seconds
        ├── num_threads:    Number of worker threads
        └── use_cache:    Whether to use cache for worker results
test-config-shell#
```

And above shell can be used like this:

```
test-config-shell#configure_terminal
test-config-shell[cfg]#workers ?
 <worker_name>    Name of the worker
test-config-shell[cfg]#workers worker-1 ?
 num_threads    Number of worker threads
 timeout        Worker timeout in seconds
 use_cache      Whether to use cache for worker results
test-config-shell[cfg]#workers worker-1 num_threads 1 timeout 1 use_cache True
Configuration updated (uncommitted). Use 'commit' to save or 'show changes' to review.
test-config-shell[cfg]#show changes
--- app_config.yaml
+++ app_config.yaml.tmp
@@ -1 +1,6 @@
-{}
+workers:
+  worker-1:
+    num_threads: 1
+    timeout: 1
+    use_cache: true
+    worker_name: worker-1
test-config-shell[cfg]#commit
Configuration committed successfully
test-config-shell[cfg]#exit
test-config-shell#
```
