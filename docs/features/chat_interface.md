# Chat Interface

The chat interface provides an interactive loop where a user sends messages
and receives responses, similar to chatting with an AI agent or LLM.

Enable it by setting `"chat"` in a field's `json_schema_extra`. The chat
field behaves like `presence` — when the user types the field name with no
value, it is set to `True` and the command passes through Pydantic
validation before entering the chat loop.

The `"chat"` value controls which parameter of the `run` method receives
the user's message:

- `"chat": True` — passes user input as `message` (default argument name).
- `"chat": "message"` — same as above, explicitly naming the argument.
- `"chat": "prompt"` — passes user input as `prompt` keyword argument.

## Basic example

```python
from typing import Any
from pydantic import BaseModel, Field
from picle import App


class ChatCommand(BaseModel):
    chat: Any = Field(
        None,
        description="Start a chat session",
        json_schema_extra={
            "chat": "message",
            "chat_prompt": "You> ",
        },
    )

    @staticmethod
    def run(message: str = None, **kwargs):
        # Replace with your LLM / agent call
        return f"Assistant: I received '{message}'"


class Root(BaseModel):
    agent: ChatCommand = Field(None, description="AI agent")
```

Starting the chat:

```
picle#agent chat
You> Hello!
Assistant: I received 'Hello!'
You> How are you?
Assistant: I received 'How are you?'
You> <Ctrl+D>
picle#
```

The loop continues until the user presses **Ctrl+D** (EOF) or types `/exit`.

!!! note
    The chat field type should be `Any` (not `StrictStr`) since entering
    chat mode sets the field value to `True` for validation purposes.

## json_schema_extra keys

| Key | Default | Description |
|-----|---------|-------------|
| `chat` | — | Set to `"message"` (or any string) to map user input to that `run` parameter, or `True` to default to `"message"`. Behaves like `presence` — sets the field value to `True` when no value is provided. |
| `chat_prompt` | `"> "` | Prompt string shown before each user input. |
| `chat_response_style` | `None` | Rich markup style applied to responses (e.g. `"green"`, `"bold cyan"`). Only used when Rich is available; no styling is applied otherwise. |
| `chat_response_prefix` | `""` | Text prepended to each response (e.g. `"AI> "`). |

## Slash commands

Lines that start with `/` are dispatched to the PICLE shell instead of the
chat function. This lets you run any shell command
without leaving the chat:

```
You> tell me a joke
Assistant: Why did the programmer quit? Because he didn't get arrays.
You> /show version
0.1.0
You> /help
...
You> /exit
picle#
```

`/exit` exits the chat loop and returns to the normal shell prompt.

## Using a custom function

You can combine `"chat"` with `"function"` to call a specific staticmethod
instead of `run`:

```python
class AgentChat(BaseModel):
    invoke: Any = Field(
        None,
        description="Talk to the agent",
        json_schema_extra={
            "chat": "message",
            "function": "ask_agent",
            "chat_prompt": "agent> ",
        },
    )

    @staticmethod
    def ask_agent(message: str = None, **kwargs):
        return f"Agent says: {message}"
```

## Rich styled responses

When Rich is installed and `use_rich` is enabled, you can style agent
responses to visually distinguish them from user input. If Rich is not
available, no styling is applied — the response prints as plain text.

```python
class StyledChat(BaseModel):
    chat: Any = Field(
        None,
        description="Chat with styled output",
        json_schema_extra={
            "chat": "message",
            "chat_prompt": "You> ",
            "chat_response_style": "green",
            "chat_response_prefix": "AI> ",
        },
    )

    @staticmethod
    def run(message: str = None, **kwargs):
        return f"I received: {message}"
```

```
You> Hello
AI> I received: Hello       <-- printed in green when Rich is available
You>
```

Any Rich console markup style is supported: `"bold cyan"`, `"italic yellow"`,
`"dim"`, etc.

## Accessing the App instance

If your chat function needs access to the PICLE app (for example to call
other commands programmatically), declare a `picle_app` parameter:

```python
@staticmethod
def run(message: str = None, picle_app=None, **kwargs):
    # picle_app is the App instance
    ...
```

The same mechanism works for `root_model` and `shell_command`.

## Result specific outputters

The `run` method can return a tuple to override how the response is
displayed, exactly like regular PICLE commands:

- `(result, outputter)` — use a custom outputter callable.
- `(result, outputter, outputter_kwargs)` — outputter with extra keyword arguments.

```python
from picle.models import Outputters


class AgentChat(BaseModel):
    chat: Any = Field(
        None,
        description="Chat with agent",
        json_schema_extra={"chat": "message"},
    )

    @staticmethod
    def run(message: str = None, **kwargs):
        response = {"role": "assistant", "content": f"Reply to: {message}"}
        return response, Outputters.outputter_rich_json
```

This works the same way as
[Result Specific Outputters](result_specific_outputters.md) for regular
commands — the chat loop applies the returned outputter to each response.

## Streaming responses

If the `run` method returns a **generator** (or any iterator), the chat loop
prints each chunk to stdout as it arrives rather than waiting for the full
response. This is essential for LLM integrations where tokens are produced
incrementally.

```python
class StreamingChat(BaseModel):
    chat: Any = Field(
        None,
        description="Chat with streaming",
        json_schema_extra={"chat": "message"},
    )

    @staticmethod
    def run(message: str = None, **kwargs):
        import openai

        client = openai.OpenAI()
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message}],
            stream=True,
        )

        def generate():
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        return generate()
```

The streaming output is written directly to stdout, flushing after each
chunk so tokens appear immediately. Pressing **Ctrl+C** during streaming
cancels the current response without exiting the chat loop.

## Exiting the chat from the run function

The chat loop normally continues until the user presses **Ctrl+D** or types
`/exit`. However, there are additional ways the chat can exit:

- **Ctrl+C** — exits the chat loop **and** terminates the current shell.
- **`return None`** — exits the chat loop and returns to the shell prompt.
- **`return True`** — exits the chat loop **and** terminates the current shell
  (same as the `exit` built-in command).

This is useful when the agent or LLM decides the conversation is finished, or
when an error condition requires leaving the chat programmatically.

```python
class GracefulChat(BaseModel):
    chat: Any = Field(
        None,
        description="Chat that can end itself",
        json_schema_extra={"chat": "message"},
    )

    @staticmethod
    def run(message: str = None, **kwargs):
        if message.lower() == "bye":
            return None  # exit chat, return to shell
        if message.lower() == "shutdown":
            return True  # exit chat and terminate shell
        return f"Echo: {message}"
```

```
picle#agent chat
> hello
Echo: hello
> bye
picle#
```
