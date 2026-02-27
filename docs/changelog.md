# 0.10.1

## BUGS

1. MAN fixing examples output when examples are anything but string

## CHANGES

1. Making mandatory fields to be at the top of help output and in bold cursor
2. To invoke multiline input mode changing command from `input` to `load-terminal`

## FEATURES

1. Adding `history` command to output commands history, adding `history_length` PicleConfig class config attribute
2. Improving message back to a user for incorrect command with suggesting possible completions
3. Enhancing errors output printed to the screen by making it to be printed in red color

---

# 0.10.0

## CHANGES

1. Dependencies updates to loosen them up
2. Adding type hints throughout and updating doc strings
3. Fixed pydantic warnings about model_fields access and about using extra arguments on fields

## FEATURES

1. Added ConfigModel model to picle to help with maintaininng configuration files using Picle interactive shell.

## BUGS

1. __init__ ~L97 -PicleConfig accessed without hasattr guard — crash for models without it
2. do_help ~L855 - Multi-word help silently discarded — never printed
3. do_help ~L857 - Unhandled FieldLooseMatchOnly/FieldKeyError exceptions
4. print_model_help - Medium	width not computed for all lines keys — misaligned output
5. default ~L1004 - Partial alias match reports empty completions list
6. do_exit ~L872 - Missing PicleConfig guard on prompt access
7. do_top ~L883 - Same missing guard

---

# 0.9.3

## CHANGES

1. Improving outputter models handling

---

# 0.9.2

## CHANGES

1. Improved value conversion logic to not convert values to integers or bool etc if field annotation is `str` or `StrictStr`
2. Updated `pyproject.toml` file with dependency version for PyYAML and Tabulate modules

---

# 0.9.1

## FEATURES

1. Extending nested outputter with capability to include tables within nested output if data is a list of dictionaries

---

# 0.9.0

## CHANGES

1. Removed support for using `Callable` annotation for calling model method
2. Removed formatters from built in models, instead need to use outputter
3. Improved pipe functions handling logic 
4. Rich is now a default outputter, can be disabled using ``use_rich`` config parameter in the root's model PicleConfig 

## FEATURES

1. Added Tabulate table outputter
2. Added `save` outputter to save results into a file
3. Added support for pipe attribute to reference `path.to.pipemodel` Python import string
