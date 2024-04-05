import unittest
import unittest.mock
import sys
import time
import picle_test_shell
import pprint

from picle import App
from enum import Enum
from typing import List, Union, Optional, Callable
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool

mock_stdin = unittest.mock.create_autospec(sys.stdin)
mock_stdout = unittest.mock.create_autospec(sys.stdout)
shell = App(picle_test_shell.Root, stdin=mock_stdin, stdout=mock_stdout)


def test_callable():
    shell.onecmd("show version")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    assert shell_output == "0.1.0\r\n"


def test_default_values():
    shell.onecmd("salt nr cli commands abc")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    assert (
        shell_output
        == "Called salt nr cli, kwargs: {'target': 'proxy:proxytype:nornir', 'tgt_type': 'pillar', 'commands': 'abc', 'plugin': 'netmiko'}\r\n"
    )


def test_presense_at_the_end():
    shell.onecmd("salt nr cli commands abc add_details")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    assert (
        shell_output
        == "Called salt nr cli, kwargs: {'target': 'proxy:proxytype:nornir', 'tgt_type': 'pillar', 'commands': 'abc', 'plugin': 'netmiko', 'add_details': True}\r\n"
    )


def test_presense_in_between():
    shell.onecmd("salt nr cli commands abc add_details hosts ceos1")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    assert (
        shell_output
        == "Called salt nr cli, kwargs: {'target': 'proxy:proxytype:nornir', 'tgt_type': 'pillar', 'commands': 'abc', 'plugin': 'netmiko', 'add_details': True, 'hosts': 'ceos1'}\r\n"
    )


def test_parse_default_values():
    models = shell.parse_command(
        "salt nr cli commands abc xyz", add_default_values=True
    )

    pprint.pprint(models)
    # [{'fields': [], 'model': Root(salt=None, show=None), 'parameter': Ellipsis},
    # {'fields': [{'name': 'target', 'values': 'proxy:proxytype:nornir'},
    # {'name': 'tgt_type', 'values': 'pillar'}],
    # 'model': <class 'picle_test_shell.model_salt'>,
    # 'parameter': 'salt'},
    # {'fields': [],
    # 'model': <class 'picle_test_shell.model_nr'>,
    # 'parameter': 'nr'},
    # {'fields': [{'field': FieldInfo(annotation=Union[Annotated[str, Strict(strict=True)], List[Annotated[str, Strict(strict=True)]]], required=True, description='CLI commands to send to devices'),
    #'name': 'commands',
    #'values': ['abc', 'xyz']},
    # {'name': 'plugin', 'values': 'netmiko'}],
    # 'model': <class 'picle_test_shell.model_nr_cli'>,
    # 'parameter': 'cli'}]

    assert models[0][1]["parameter"] == "salt"
    assert (
        models[0][1]["fields"][0]["name"] == "target"
        and models[0][1]["fields"][0]["values"] == "proxy:proxytype:nornir"
    )
    assert (
        models[0][1]["fields"][1]["name"] == "tgt_type"
        and models[0][1]["fields"][1]["values"] == "pillar"
    )

    assert models[0][2]["parameter"] == "nr"
    assert models[0][2]["fields"] == []

    assert models[0][3]["parameter"] == "cli"
    assert models[0][3]["fields"][0]["name"] == "commands" and models[0][3]["fields"][0][
        "values"
    ] == ["abc", "xyz"]
    assert (
        models[0][3]["fields"][1]["name"] == "plugin"
        and models[0][3]["fields"][1]["values"] == "netmiko"
    )


def test_pipe_function_include():
    shell.onecmd("show joke | include Why")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]
    
    print(f" shell output: '{shell_output}'")
    
    assert "Why did the network engineer always carry a ladder?" in shell_output
    
    
def test_pipe_function_exclude():
    shell.onecmd("show joke | exclude Why")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]
    
    print(f" shell output: '{shell_output}'")
    
    assert "Why did the network engineer always carry a ladder?" not in shell_output
    
    
def test_multiple_pipe_functions():
    shell.onecmd("show joke | include d | exclude End")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]
    
    print(f" shell output: '{shell_output}'")
    
    assert (
        "Why did the network engineer always carry a ladder?" in shell_output and
        'Because he wanted to reach the highest levels of connectivity... and occasionally fix the "cloud" when it crashed!' in shell_output and not
        "End" in shell_output
    )
    