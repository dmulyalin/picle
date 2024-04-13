import unittest
import unittest.mock
import sys
import time
import picle_test_shell
import pprint
import pytest

from picle import App
from enum import Enum
from typing import List, Union, Optional, Callable
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool

mock_stdin = unittest.mock.create_autospec(sys.stdin)
mock_stdout = unittest.mock.create_autospec(sys.stdout)
shell = App(picle_test_shell.Root, stdin=mock_stdin, stdout=mock_stdout)


def test_callable():
    shell.onecmd("top")  # go to top
    shell.onecmd("show version")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    assert shell_output == "0.1.0\r\n"


def test_default_values():
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cli commands abc")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
        ]
    )


def test_default_values_from_subshell():
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cli")  # go to subshell
    shell.onecmd("commands abc")  # call command
    shell_output = mock_stdout.write.call_args_list[-1][0][0]
    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
        ]
    )


def test_presense_at_the_end():
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cli commands abc add_details")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
            "'add_details': True",
        ]
    )


def test_presense_in_between():
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cli commands abc add_details hosts ceos1")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
            "'add_details': True",
            "'hosts': 'ceos1'",
        ]
    )


def test_pipe_function_include():
    shell.onecmd("top")  # go to top
    shell.onecmd("show joke | include Why")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "Why did the network engineer always carry a ladder?" in shell_output


def test_pipe_function_exclude():
    shell.onecmd("top")  # go to top
    shell.onecmd("show joke | exclude Why")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "Why did the network engineer always carry a ladder?" not in shell_output


def test_multiple_pipe_functions():
    shell.onecmd("top")  # go to top
    shell.onecmd("show joke | include d | exclude End")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        "Why did the network engineer always carry a ladder?" in shell_output
        and 'Because he wanted to reach the highest levels of connectivity... and occasionally fix the "cloud" when it crashed!'
        in shell_output
        and not "End" in shell_output
    )


def test_processors_formatter_pprint():
    """data_pprint uses Formatters.formatter_pprint processor to pprint the output"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_pprint")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        """{   'even': {'more': {'dictionary': 'data'}},
    'more': {'dictionary': ['data']},
    'some': {'dictionary': {'data': None}}}"""
        in shell_output
    )


def test_pipe_formatter_pprint():
    """pprint pipe function uses Formatters.formatter_pprint function to pprint the output"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | pprint")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        """{   'even': {'more': {'dictionary': 'data'}},
    'more': {'dictionary': ['data']},
    'some': {'dictionary': {'data': None}}}"""
        in shell_output
    )


def test_pipe_formatter_json_and_alias():
    """json pipe function uses Formatters.formatter_json function to print
    json output, also model uses json_ and field has alias="json" defines"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | json")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        """{
    "even": {
        "more": {
            "dictionary": "data"
        }
    },
    "more": {
        "dictionary": [
            "data"
        ]
    },
    "some": {
        "dictionary": {
            "data": null
        }
    }
}"""
        in shell_output
    )


def test_pipe_formatter_yaml():
    """yaml pipe function uses Formatters.formatter_yaml function to print
    yaml output"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | yaml")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        """even:
  more:
    dictionary: data
more:
  dictionary:
  - data
some:
  dictionary:
    data: null"""
        in shell_output
    )


def test_outputter_rich_json():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_rich_json")

    assert True


def test_PicleConfig_processor_with_run_method():
    """
    model_nr_cfg has processor attribute defined within PicleConfig class,
    this test tests its execution
    """
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cfg commands bla")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert (
        """{
    "commands": "bla",
    "plugin": "netmiko",
    "target": "proxy:proxytype:nornir",
    "tgt_type": "pillar"
}"""
        in shell_output
    )


def test_PicleConfig_outputter_with_run_method():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("test_PicleConfig_outputter_with_run_method string_argument bla")

    assert True


def test_subshell_handling():
    shell.onecmd("top")  # go to top

    # 1 go to subshell
    shell.onecmd("salt nr cli")

    print(f"Current shell prompt: '{shell.prompt}'")

    assert shell.prompt == "salt[nr-cli]#"

    # 2 run command in subshell
    shell.onecmd("commands abc add_details")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
            "'add_details': True",
        ]
    )

    # 3 go back to the top
    shell.onecmd("top")

    print(f"Current shell prompt: '{shell.prompt}'")

    assert shell.prompt == "picle#"


def test_shell_exit_defaults_handling():
    shell.onecmd("top")  # go to top
    shell.shell_defaults.clear()

    # go to subshell
    shell.onecmd("salt nr cli")
    print(f"Current shell prompt: '{shell.prompt}', defaults '{shell.shell_defaults}'")
    assert shell.shell_defaults == {
        "target": "proxy:proxytype:nornir",
        "tgt_type": "pillar",
    }

    # exit to top
    shell.onecmd("exit")
    shell.onecmd("exit")
    print(f"Current shell prompt: '{shell.prompt}', defaults '{shell.shell_defaults}'")
    assert shell.shell_defaults == {}


def test_shell_top_defaults_handling():
    shell.onecmd("top")  # go to top
    shell.shell_defaults.clear()

    # go to subshell
    shell.onecmd("salt nr cli")
    print(f"Current shell prompt: '{shell.prompt}', defaults '{shell.shell_defaults}'")
    assert shell.shell_defaults == {
        "target": "proxy:proxytype:nornir",
        "tgt_type": "pillar",
    }

    # exit to top
    shell.onecmd("top")
    print(f"Current shell prompt: '{shell.prompt}', defaults '{shell.shell_defaults}'")
    assert shell.shell_defaults == {}


def test_pipe_formatter_kv():
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | kv")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        """some: {'dictionary': {'data': None}}
 more: {'dictionary': ['data']}
 even: {'more': {'dictionary': 'data'}}"""
        in shell_output
    )


def test_model_run_kwargs_unpacking():
    shell.onecmd("top")  # go to top
    # give command with plugin keyword that is part of defaults
    # this command prior to 0.5.2 would fail to execute due to
    # issue with improper arguments unpacking
    shell.onecmd("salt nr cli commands abc plugin netmiko")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert all(
        k in shell_output
        for k in [
            "Called salt nr cli, kwargs:",
            "'target': 'proxy:proxytype:nornir'",
            "'tgt_type': 'pillar'",
            "'commands': 'abc'",
            "'plugin': 'netmiko'",
        ]
    )
