# PICLE - Python Interactive Command Line Shells

PICLE is a module to construct interactive command line shell
applications using Pydantic models.

Built on top of Python's standard library 
[CMD module](https://docs.python.org/3/library/cmd.html) and 
uses [Pydantic](https://docs.pydantic.dev/) models to construct 
shell environments.

Welcome to [documentation](https://dmulyalin.github.io/picle/) to
explore it further.

# Comparison With Other Projects

[python-nubia](https://github.com/facebookarchive/python-nubia) by 
Facebook - unfortunately this project no longer maintained, it also 
provides no integration with Pydantic.

Why not [python-fire](https://github.com/google/python-fire), 
[click](https://github.com/pallets/click) or 
[argparse](https://docs.python.org/3/library/argparse.html) - 
all these libraries are great for building command line tools, 
but they provide no support for interactive shell or input 
comprehensive validation supported by Pydantic.

Why not 
[prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) 
or [textual](https://github.com/Textualize/textual)
- those are extremely good libraries for building Terminal User Interface 
(TUI) applications but they provide no support for interactive shell and 
Pydantic validation of input.