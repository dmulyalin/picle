import unittest
import unittest.mock
import sys
import time
import pprint
import pytest

from picle import App
from enum import Enum
from typing import List, Union, Optional, Callable
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool
from .picle_test_shell import Root

mock_stdin = unittest.mock.create_autospec(sys.stdin)
mock_stdout = unittest.mock.create_autospec(sys.stdout)
shell = App(Root, stdin=mock_stdin, stdout=mock_stdout)


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


def test_presence_at_the_end():
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


def test_presence_in_between():
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

    assert """{   'even': {'more': {'dictionary': 'data'}},
    'list': [   {'more': {'dictionary': 'data'}},
                {'more': {'dictionary': 'data'}}],
    'more': {'dictionary': ['data']},
    'some': {'dictionary': {'data': None}}}""" in shell_output


def test_pipe_formatter_pprint():
    """pprint pipe function uses Formatters.formatter_pprint function to pprint the output"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | pprint")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert """{   'even': {'more': {'dictionary': 'data'}},
    'list': [   {'more': {'dictionary': 'data'}},
                {'more': {'dictionary': 'data'}}],
    'more': {'dictionary': ['data']},
    'some': {'dictionary': {'data': None}}}""" in shell_output


def test_pipe_formatter_json_and_alias():
    """json pipe function uses Formatters.formatter_json function to print
    json output, also model uses json_ and field has alias="json" defines"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | json")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert """{
    "even": {
        "more": {
            "dictionary": "data"
        }
    },
    "list": [
        {
            "more": {
                "dictionary": "data"
            }
        },
        {
            "more": {
                "dictionary": "data"
            }
        }
    ],
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
}""" in shell_output


def test_alias_handling():
    """model field has alias with dashes, while field uses underscores"""
    shell.onecmd("top")  # go to top
    shell.onecmd("test_alias_handling foo-bar-command bla")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "{'foo_bar_command': 'bla'}" in shell_output


def test_alias_handling_nested_model():
    shell.onecmd("top")  # go to top
    shell.onecmd(
        "test_alias_handling nested_command enter-command foo command_no_alias bar"
    )

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "{'command_with_alias': 'foo', 'command_no_alias': 'bar'}" in shell_output

    """model field has alias with dashes, while field uses underscores"""
    shell.onecmd("top")  # go to top
    shell.onecmd("test_alias_handling foo-bar-command bla")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "{'foo_bar_command': 'bla'}" in shell_output


def test_alias_handling_at_the_top():
    shell.onecmd("top")  # go to top
    shell.onecmd("test-alias-handling-top foo")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "{'test_alias_handling_top': 'foo'}" in shell_output


def test_alias_handling_mandatory_field():
    shell.onecmd("top")  # go to top
    shell.onecmd(
        "test_alias_handling mandatory_field_test mandatory-field-with-alias bla"
    )

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert "{'mandatory_field_with_alias': 'bla'}" in shell_output


def test_pipe_formatter_yaml():
    """yaml pipe function uses Formatters.formatter_yaml function to print
    yaml output"""
    shell.onecmd("top")  # go to top
    shell.onecmd("show data | yaml")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert """even:
  more:
    dictionary: data
list:
- more:
    dictionary: data
- more:
    dictionary: data
more:
  dictionary:
  - data
some:
  dictionary:
    data: null""" in shell_output


def test_outputter_rich_json():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_rich_json")

    assert True


def test_outputter_nested():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_output_nested")

    assert True


def test_outputter_nested_with_tables():
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_output_nested_tables")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert all(k in shell_output for k in ["key1_value3", "nested_data"])


def test_PicleConfig_processor_with_run_method():
    """
    model_nr_cfg has processor attribute defined within PicleConfig class,
    this test tests its execution
    """
    shell.onecmd("top")  # go to top
    shell.onecmd("salt nr cfg commands bla")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert """{
    "commands": "bla",
    "plugin": "netmiko",
    "target": "proxy:proxytype:nornir",
    "tgt_type": "pillar"
}""" in shell_output


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

    assert """some: {'dictionary': {'data': None}}
 more: {'dictionary': ['data']}
 even: {'more': {'dictionary': 'data'}}""" in shell_output


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


def test_outputter_rich_table():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_rich_table")

    assert True


def test_outputter_rich_table_with_kwargs():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("show data_rich_table")

    assert True


def test_outputter_rich_table_with_kwargs():
    # outputter prints to terminal bypassing stdout, hence no output to test

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd(
        "test_outputter_rich_table_with_PicleConfig_kwargs string_argument bla"
    )

    assert True


def test_nested_model_run_with_no_kwargs():
    shell.onecmd("top")  # go to top
    # give command with no keywords to verify handling of
    # model that has run method but no command arguments provided
    shell.onecmd("show XYZ")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f" shell output: '{shell_output}'")

    assert (
        "[{'name': 'name3', 'status': 'dead', 'keepalive': '123'}, {'name': 'name1', 'status': 'alive', 'keepalive': '123'}, {'name': 'name2', 'status': 'any', 'keepalive': '123'}]"
        in shell_output
    )


def test_json_field():
    shell.onecmd("top")  # go to top
    shell.onecmd(
        """test_json_input data {"person":{"name":"John","age":30,"contacts":[ {"arg":"email","value":"john@example.com"} ] } }  arg foo"""
    )

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")
    assert (
        """{'data': '{"person":{"name":"John","age":30,"contacts":[ {"arg":"email","value":"john@example.com"}]}}', 'arg': 'foo'}"""
        in shell_output
    )


def test_json_field_boolean_true():
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_json_input data true arg foo""")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert """{'data': 'true', 'arg': 'foo'}""" in shell_output


def test_json_field_boolean_false():
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_json_input data false arg foo""")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert """{'data': 'false', 'arg': 'foo'}""" in shell_output


def test_json_field_boolean_null():
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_json_input data null arg foo""")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert """{'data': 'null', 'arg': 'foo'}""" in shell_output


def test_multiline_input_with_inline_value():
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_multiline_input data foo arg bar""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert "{'data': 'foo', 'arg': 'bar'}" in shell_output


def test_outputter_result_specific():
    # outputter prints to terminal bypassing stdout, hence no output to test, just test that runs with no error

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("test_result_specific_outputter data foo arg bar")

    assert True


def test_outputter_result_specific_no_kwargs():
    # outputter prints to terminal bypassing stdout, hence no output to test, just test that runs with no error

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("test_result_specific_outputter_no_kwargs data foo arg bar")

    assert True


def test_single_quote_command_collection():
    # outputter prints to terminal bypassing stdout, hence no output to test, just test that runs with no error

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_command_values command 'show version | match "Juniper: "' """)

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert """{'command': 'show version | match "Juniper: "'}""" == shell_output.strip()


def test_presence_handling_for_next_model():
    # outputter prints to terminal bypassing stdout, hence no output to test, just test that runs with no error

    # just verify command run with no exceptions raised
    shell.onecmd("top")  # go to top
    shell.onecmd("""salt nr cli commands "show clock" table next_model some bla""")

    shell_output = mock_stdout.write.call_args_list[-1][0][0]

    print(f"shell output: '{shell_output}'")

    assert (
        """Called salt nr cli, kwargs: {'target': 'proxy:proxytype:nornir', 'tgt_type': 'pillar', 'plugin': 'netmiko', 'commands': 'show clock', 'table': 'brief', 'some': 'bla'}"""
        == shell_output.strip()
    )


def test_model_mount():
    class test_mount_model(BaseModel):
        param: StrictStr = Field(None, description="string")

        @staticmethod
        def run(**kwargs):
            return kwargs

    # mount model and test it runs
    shell.model_mount(test_mount_model, "mount_model_top")
    shell.onecmd("top")  # go to top
    shell.onecmd("""mount_model_top param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert shell_output == "{'param': 'bla'}"

    # remove model
    shell.model_remove("mount_model_top")
    shell.onecmd("""mount_model_top param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "Incorrect command" in shell_output


def test_model_mount_with_alias():
    class test_mount_model(BaseModel):
        param: StrictStr = Field(None, description="string")

        @staticmethod
        def run(**kwargs):
            return kwargs

    # mount model and test it runs
    shell.model_mount(test_mount_model, "mount_model_top", alias="mount-model-top")
    shell.onecmd("top")  # go to top
    shell.onecmd("""mount-model-top param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert shell_output == "{'param': 'bla'}"

    # remove model
    shell.model_remove("mount_model_top")
    shell.onecmd("""mount-model-top param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "Incorrect command" in shell_output


def test_model_mount_nested():
    class test_mount_model(BaseModel):
        param: StrictStr = Field(None, description="string")

        @staticmethod
        def run(**kwargs):
            return kwargs

    # mount model and test it runs
    shell.model_mount(test_mount_model, ["salt", "mount_model_nested"])
    shell.onecmd("top")  # go to top
    shell.onecmd("""salt mount_model_nested param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "'param': 'bla'" in shell_output

    # remove model
    shell.model_remove(["salt", "mount_model_nested"])
    shell.onecmd("""salt mount_model_nested param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "'param': 'bla'" not in shell_output


def test_model_remove_wrong_path():
    class test_mount_model(BaseModel):
        param: StrictStr = Field(None, description="string")

        @staticmethod
        def run(**kwargs):
            return kwargs

    # mount model and test it runs
    shell.model_mount(test_mount_model, ["salt", "mount_model_nested"])
    shell.onecmd("top")  # go to top
    shell.onecmd("""salt mount_model_nested param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "'param': 'bla'" in shell_output

    # try to remove model at wrong path
    with pytest.raises(KeyError):
        shell.model_remove(["salt", "wrong_name"])


def test_model_mount_nested_wrong_path():
    class test_mount_model(BaseModel):
        param: StrictStr = Field(None, description="string")

        @staticmethod
        def run(**kwargs):
            return kwargs

    with pytest.raises(KeyError):
        shell.model_mount(test_mount_model, ["salt", "foo", "bar"])


def test_model_mount_commands():
    # mount model and test it runs
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_mount_model mount_add foo""")
    shell.onecmd("""foo param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "'param': 'bla'" in shell_output

    # remove model
    shell.onecmd("""test_mount_model mount_remove foo""")
    shell.onecmd("""foo param bla""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "'param': 'bla'" not in shell_output


def test_enum_and_field_with_same_name():
    shell.onecmd("top")  # go to top
    shell.onecmd("""test_enum_and_field_with_same_name task cli client bla""")

    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()

    print(f"shell output: '{shell_output}'")

    assert "{'task': 'cli', 'client': 'bla'}" in shell_output


def test_source_has_boolean_in_a_list():
    shell.onecmd("top")  # go to top

    shell.onecmd("""test_source_has_boolean_in_a_list value False""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': False}" in shell_output

    shell.onecmd("""test_source_has_boolean_in_a_list value True""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': True}" in shell_output

    shell.onecmd("""test_source_has_boolean_in_a_list value None""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': None}" in shell_output

    shell.onecmd("""test_source_has_boolean_in_a_list value foo""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': 'foo'}" in shell_output

    shell.onecmd("""test_source_has_boolean_in_a_list value bar""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': 'bar'}" in shell_output


def test_enum_has_boolean_in_a_list():
    shell.onecmd("top")  # go to top

    shell.onecmd("""test_enum_has_boolean_in_a_list value False""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': False}" in shell_output

    shell.onecmd("""test_enum_has_boolean_in_a_list value True""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': True}" in shell_output

    shell.onecmd("""test_enum_has_boolean_in_a_list value foo""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value': 'foo'}" in shell_output


def test_tabulate_table():
    shell.onecmd("top")  # go to top

    shell.onecmd("""show data_list | table""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")

    assert all(
        l in shell_output
        for l in [
            "+----+--------+-------------+-------------+",
            "|    | name   | key1        | key2        |",
            "+====+========+=============+=============+",
            "|  1 | name3  | key1_value3 | key2_value3 |",
            "|  2 | name1  | key1_value1 | key2_value1 |",
            "|  3 | name2  | key1_value2 | key2_value2 |",
        ]
    )


def test_tabulate_table_tablefmt_plain():
    shell.onecmd("top")  # go to top

    shell.onecmd("""show data_list | table tablefmt plain""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")

    assert all(
        l in shell_output
        for l in [
            "name    key1         key2",
            " 1  name3   key1_value3  key2_value3",
            " 2  name1   key1_value1  key2_value1",
            " 3  name2   key1_value2  key2_value2",
        ]
    )


def test_integer_converstion_for_strictstr_field():
    shell.onecmd("top")  # go to top

    shell.onecmd("""test_integer_converstion_for_strictstr_field value_StrictStr 123""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value_StrictStr': '123'}" in shell_output

    shell.onecmd("""test_integer_converstion_for_strictstr_field value_str 123""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value_str': '123'}" in shell_output

    shell.onecmd("""test_integer_converstion_for_strictstr_field value_StrictInt 123""")
    shell_output = mock_stdout.write.call_args_list[-1][0][0].strip()
    print(f"shell output: '{shell_output}'")
    assert "{'value_StrictInt': 123}" in shell_output
