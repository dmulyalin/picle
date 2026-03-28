# Shell Commands

PICLE provides a built-in `shell` command to execute operating system shell commands directly from the interactive prompt.

This command works on Windows and Linux.

## Basic Usage

Use the command as:

```text
shell <command>
```

Examples:

```text
picle#shell echo hello
hello

picle#shell python --version
Python 3.x.x
```

The command is global, so it can be used from the top prompt and from subshells.

## Platform Behavior

`shell` executes commands via Python `subprocess.run(...)` with `shell=True`.

- On Windows, commands run through the system shell (for example `cmd.exe`).
- On Linux, commands run through the default shell (for example `/bin/sh`).

This means you can use native shell commands for each platform.

```text
# Windows
picle#shell dir

# Linux
picle#shell ls -la
```

## Output And Errors

PICLE captures and prints both standard output and error output:

- `stdout` is printed as regular command output.
- `stderr` is printed using error output formatting.
- If a command exits with a non-zero code and produced no `stderr`, PICLE prints the exit code.

If no command is provided, PICLE returns:

```text
shell command is required
```

## Getting Help

Use built-in help to see command documentation:

```text
picle#help shell
```

## Security Note

`shell` runs commands on the host operating system, so avoid passing untrusted input directly into it.
