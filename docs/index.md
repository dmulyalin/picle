# PICLE - Python Interactive Command Line Shells

PICLE is a module to construct interactive command line shell
applications.

PICLE build on top of Python standard library 
[CMD module](https://docs.python.org/3/library/cmd.html) and 
uses [Pydantic](https://docs.pydantic.dev/latest/) models to 
construct shell environments. 

If the ``readline`` module is loaded 
([pyreadline3](https://pypi.org/project/pyreadline3/)), input will 
automatically inherit bash-like history-list editing (e.g. 
Control-P scrolls back to the last command, Control-N forward 
to the next one, Control-F moves the cursor to the right 
non-destructively, Control-B moves the cursor to the left 
non-destructively, etc.).

# Installation

Install [PICLE from PyPI](https://pypi.org/project/picle/) using pip

```
pip install picle
```