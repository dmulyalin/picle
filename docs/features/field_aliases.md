# Field Aliases

PICLE resolves command tokens by canonical field name, `alias`, or `serialization_alias`.

This lets you keep Python-friendly field names in code while exposing shell-friendly names such as dashed commands.

## Example Model

```python
from pydantic import BaseModel, Field, StrictStr


class LoginOptions(BaseModel):
    key_path: StrictStr = Field(
        None,
        description="SSH private key",
        alias="key-path",
    )
    user_name: StrictStr = Field(
        ...,
        description="Remote username",
        serialization_alias="user-name",
    )
    
    @staticmethod
    def run(**kwargs):
        return kwargs

class ConnectCommand(BaseModel):
    transport_mode: StrictStr = Field(
        None,
        description="Connection transport",
        alias="transport-mode",
    )
    login: LoginOptions = Field(None, description="Login parameters")


class Root(BaseModel):
    device_tools: ConnectCommand = Field(
        None,
        description="Device operations",
        alias="device-tools",
    )
```

## Command Examples

Top-level and field aliases are accepted anywhere along the path:

```text
picle#device-tools transport-mode ssh
{'transport_mode': 'ssh'}
```

Nested aliases work the same way:

```text
picle#device-tools login key-path ~/.ssh/id_ed25519 user-name admin
{'key_path': '~/.ssh/id_ed25519', 'user_name': 'admin'}
```

You can freely mix canonical names and aliases in the same command:

```text
picle#device_tools login key-path ~/.ssh/id_ed25519 user_name admin
```

## What Your Code Receives

Aliases affect command resolution, help, completion, and dotted paths used by `man json-schema`.

The callable still receives canonical field names in `kwargs`.

That is why the examples above return keys such as `transport_mode` and `user_name`, even though the shell input uses dashed names.