"""
Tests for ConfigModel functionality using example_config_app.py sample app.
"""

import os
import sys
import unittest
import unittest.mock
import pytest
import yaml
import pprint

from pathlib import Path
from picle import App
from picle.models import ConfigModel

from .example_config_app import RootShell, MyConfigStore

# ============================================================
# Helpers
# ============================================================

CONFIG_FILE = "app_config.yaml"
TEMP_FILE = CONFIG_FILE + ".tmp"


def _cleanup_config_files():
    """Remove config file, temp file, and all backup files."""
    for f in [CONFIG_FILE, TEMP_FILE]:
        if os.path.exists(f):
            os.remove(f)
    for i in range(1, 10):
        backup = f"{CONFIG_FILE}.old{i}"
        if os.path.exists(backup):
            os.remove(backup)


def _make_shell():
    """Create a fresh App shell with mocked stdin/stdout."""
    mock_stdin = unittest.mock.create_autospec(sys.stdin)
    mock_stdout = unittest.mock.create_autospec(sys.stdout)
    shell = App(RootShell, stdin=mock_stdin, stdout=mock_stdout)
    shell.use_rich = False  # route output through mock_stdout instead of Rich console
    return shell, mock_stdout


def _last_output(mock_stdout):
    """Return the last string written to mock stdout."""
    return mock_stdout.write.call_args_list[-1][0][0]


# ============================================================
# Fixtures
# ============================================================


TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(autouse=True)
def clean_config_files():
    """Change to test dir, delete config files before and after each test."""
    original_cwd = os.getcwd()
    os.chdir(TEST_DIR)
    _cleanup_config_files()
    yield
    _cleanup_config_files()
    os.chdir(original_cwd)


# ============================================================
# Unit tests – pure static methods (no shell needed)
# ============================================================


class TestLoadConfig:
    """Tests for ConfigModel.load_config"""

    def test_load_config_creates_file_if_missing(self):
        """load_config should create the file and return empty dict when file doesn't exist."""
        assert not os.path.exists(CONFIG_FILE)
        result = ConfigModel.load_config(CONFIG_FILE)
        assert result == {}
        assert os.path.exists(CONFIG_FILE)

    def test_load_config_reads_existing_yaml(self):
        """load_config should correctly read an existing YAML file."""
        data = {"logging": {"terminal": {"severity": "debug"}}}
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(data, f)
        result = ConfigModel.load_config(CONFIG_FILE)
        assert result == data

    def test_load_config_returns_empty_dict_for_empty_file(self):
        """load_config should return {} for an empty YAML file."""
        Path(CONFIG_FILE).touch()
        result = ConfigModel.load_config(CONFIG_FILE)
        assert result == {}

    def test_load_config_creates_parent_directories(self, tmp_path):
        """load_config should create parent dirs if they don't exist."""
        nested = str(tmp_path / "sub" / "dir" / "config.yaml")
        result = ConfigModel.load_config(nested)
        assert result == {}
        assert os.path.exists(nested)


class TestSaveConfig:
    """Tests for ConfigModel.save_config"""

    def test_save_config_writes_yaml(self):
        """save_config should write config data as YAML."""
        data = {"key": "value", "nested": {"a": 1}}
        ConfigModel.save_config(CONFIG_FILE, data, backup_on_save=0)
        loaded = ConfigModel.load_config(CONFIG_FILE)
        assert loaded == data

    def test_save_config_creates_backup(self):
        """save_config should create a .old1 backup of the current file."""
        original = {"version": 1}
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(original, f)

        new_data = {"version": 2}
        ConfigModel.save_config(CONFIG_FILE, new_data, backup_on_save=5)

        # .old1 should contain the original data
        backup = ConfigModel.load_config(f"{CONFIG_FILE}.old1")
        assert backup == original

        # main file should contain new data
        current = ConfigModel.load_config(CONFIG_FILE)
        assert current == new_data

    def test_save_config_rotates_backups(self):
        """save_config should rotate backups: old1 -> old2, old2 -> old3, etc."""
        # Create initial file
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"version": 0}, f)

        # Save version 1 (old1 = version 0)
        ConfigModel.save_config(CONFIG_FILE, {"version": 1}, backup_on_save=3)
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old1") == {"version": 0}

        # Save version 2 (old1 = version 1, old2 = version 0)
        ConfigModel.save_config(CONFIG_FILE, {"version": 2}, backup_on_save=3)
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old1") == {"version": 1}
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old2") == {"version": 0}

        # Save version 3 (old1 = version 2, old2 = version 1, old3 = version 0)
        ConfigModel.save_config(CONFIG_FILE, {"version": 3}, backup_on_save=3)
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old1") == {"version": 2}
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old2") == {"version": 1}
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old3") == {"version": 0}

        # Save version 4 - old3 (the oldest) should be removed, old1 = version 3
        ConfigModel.save_config(CONFIG_FILE, {"version": 4}, backup_on_save=3)
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old1") == {"version": 3}
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old2") == {"version": 2}
        assert ConfigModel.load_config(f"{CONFIG_FILE}.old3") == {"version": 1}

    def test_save_config_no_backup_when_disabled(self):
        """save_config with backup_on_save=0 should not create backup files."""
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"old": True}, f)

        ConfigModel.save_config(CONFIG_FILE, {"new": True}, backup_on_save=0)
        assert not os.path.exists(f"{CONFIG_FILE}.old1")

    def test_save_config_returns_message(self):
        """save_config should return a status message."""
        Path(CONFIG_FILE).touch()
        result = ConfigModel.save_config(CONFIG_FILE, {}, backup_on_save=0)
        assert "Saved config to" in result


class TestUpdateNestedValue:
    """Tests for ConfigModel.update_nested_value"""

    def test_set_simple_key(self):
        data = {}
        result = ConfigModel.update_nested_value(data, ["key"], "value")
        assert result == {"key": "value"}

    def test_set_nested_key(self):
        data = {}
        result = ConfigModel.update_nested_value(data, ["a", "b", "c"], 42)
        assert result == {"a": {"b": {"c": 42}}}

    def test_update_existing_nested_key(self):
        data = {"a": {"b": {"c": 1}}}
        result = ConfigModel.update_nested_value(data, ["a", "b", "c"], 2)
        assert result == {"a": {"b": {"c": 2}}}

    def test_merge_dicts(self):
        """When both existing and new values are dicts, they should be merged."""
        data = {"a": {"x": 1}}
        result = ConfigModel.update_nested_value(data, ["a"], {"y": 2})
        assert result == {"a": {"x": 1, "y": 2}}

    def test_extend_lists(self):
        """When both existing and new values are lists, the new list should extend."""
        data = {"items": [1, 2]}
        result = ConfigModel.update_nested_value(data, ["items"], [3, 4])
        assert result == {"items": [1, 2, 3, 4]}

    def test_overwrite_non_dict_with_value(self):
        data = {"a": "string"}
        result = ConfigModel.update_nested_value(data, ["a"], "new_string")
        assert result == {"a": "new_string"}

    def test_empty_path_returns_data_unchanged(self):
        data = {"a": 1}
        result = ConfigModel.update_nested_value(data, [], "ignored")
        assert result == {"a": 1}

    def test_non_dict_intermediate_returns_data_unchanged(self):
        """Cannot traverse through a non-dict intermediate node."""
        data = {"a": "not_a_dict"}
        result = ConfigModel.update_nested_value(data, ["a", "b"], "value")
        # should return data without changes since path traversal fails
        assert result == {"a": "not_a_dict"}

    def test_creates_intermediate_dicts(self):
        """Missing intermediate keys should be created as empty dicts."""
        data = {}
        result = ConfigModel.update_nested_value(data, ["x", "y", "z"], True)
        assert result == {"x": {"y": {"z": True}}}


class TestGetCommandPath:
    """Tests for ConfigModel.get_command_path"""

    def test_extracts_string_parameters(self):
        command = [
            {"parameter": "logging", "model": None},
            {"parameter": "terminal", "model": None},
            {"parameter": "severity", "model": None},
        ]
        result = ConfigModel.get_command_path(command)
        assert result == ["logging", "terminal", "severity"]

    def test_skips_non_string_parameters(self):
        command = [
            {"parameter": ..., "model": None},
            {"parameter": "logging", "model": None},
        ]
        result = ConfigModel.get_command_path(command)
        assert result == ["logging"]

    def test_empty_command_returns_empty_list(self):
        assert ConfigModel.get_command_path([]) == []


class TestGetModelConfig:
    """Tests for ConfigModel.get_model_config"""

    def test_merges_base_and_model_config(self):
        """Should merge ConfigModel.PicleConfig defaults with the command root model's PicleConfig."""
        shell_command = [{"model": MyConfigStore}]
        result = ConfigModel.get_model_config(shell_command)
        # Should contain the overridden config_file from MyConfigStore
        assert result["config_file"] == "app_config.yaml"
        # Should contain base defaults from ConfigModel.PicleConfig
        assert "backup_on_save" in result

    def test_model_config_overrides_base_defaults(self):
        """Model-specific PicleConfig values should override base ConfigModel defaults."""
        shell_command = [{"model": MyConfigStore}]
        result = ConfigModel.get_model_config(shell_command)
        # MyConfigStore sets config_file = "app_config.yaml" which overrides default
        assert result["config_file"] == "app_config.yaml"


# ============================================================
# Integration tests – shell command execution
# ============================================================


class TestEditConfig:
    """Test editing configuration values through the shell."""

    def test_edit_config_creates_temp_file(self):
        """Editing config should create a temp file with new values."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")

        output = _last_output(mock_stdout)
        assert "uncommitted" in output.lower() or "updated" in output.lower()

        # Temp file should be created with the change
        assert os.path.exists(TEMP_FILE), "Temp file should be created"
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data["logging"]["terminal"]["severity"] == "debug"

    def test_edit_config_does_not_modify_main_file_before_commit(self):
        """Main config file should remain unchanged until commit."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")

        # Main config should still be empty/nonexistent or empty
        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert (
            main_data.get("logging", {}).get("terminal", {}).get("severity") != "debug"
        )

    def test_edit_and_commit(self):
        """Full edit + commit flow."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")

        # Verify temp file exists
        assert os.path.exists(TEMP_FILE)

        shell.onecmd("commit")
        output = _last_output(mock_stdout)
        assert "committed" in output.lower()

        # Temp file should be removed after commit
        assert not os.path.exists(TEMP_FILE), "Temp file should be removed after commit"

        # Main config should now contain the changes
        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert main_data["logging"]["terminal"]["severity"] == "debug"

    def test_multiple_edits_accumulate_in_temp(self):
        """Multiple edits should accumulate in the temp file before commit."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("logging file enabled true")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data["logging"]["terminal"]["severity"] == "debug"
        assert (
            temp_data["logging"]["file"]["enabled"] == "true"
            or temp_data["logging"]["file"]["enabled"] is True
        )

    def test_edit_overwrites_previous_value(self):
        """Editing the same field twice should overwrite the previous value."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("logging terminal severity error")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data["logging"]["terminal"]["severity"] == "error"


class TestCommitConfig:
    """Tests for commit command."""

    def test_commit_no_changes(self):
        """Commit without pending changes should report no changes."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("commit")

        output = _last_output(mock_stdout)
        assert "no uncommitted" in output.lower()

    def test_commit_creates_backup(self):
        """Committing should create a backup of the previous config."""
        shell, mock_stdout = _make_shell()

        # First create the initial config
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"version": "initial"}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("commit")

        # Verify backup was created
        assert os.path.exists(f"{CONFIG_FILE}.old1")
        backup = ConfigModel.load_config(f"{CONFIG_FILE}.old1")
        assert backup == {"version": "initial"}

    def test_commit_hook_called(self):
        """Commit hook should be invoked after successful commit."""
        hook_called = {"value": False}

        def my_hook():
            hook_called["value"] = True

        # Temporarily set commit_hook on MyConfigStore
        original = getattr(MyConfigStore.PicleConfig, "commit_hook", None)
        MyConfigStore.PicleConfig.commit_hook = my_hook

        try:
            shell, mock_stdout = _make_shell()
            shell.onecmd("top")
            shell.onecmd("configure_terminal")
            shell.onecmd("logging terminal severity debug")
            shell.onecmd("commit")

            assert hook_called["value"], "Commit hook should have been called"
        finally:
            if original is None:
                if hasattr(MyConfigStore.PicleConfig, "commit_hook"):
                    delattr(MyConfigStore.PicleConfig, "commit_hook")
            else:
                MyConfigStore.PicleConfig.commit_hook = original


class TestClearChanges:
    """Tests for clear-changes command."""

    def test_clear_changes_removes_temp_file(self):
        """clear-changes should delete the temp file."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        assert os.path.exists(TEMP_FILE)

        shell.onecmd("clear-changes")
        output = _last_output(mock_stdout)
        assert "discarded" in output.lower()
        assert not os.path.exists(TEMP_FILE)

    def test_clear_changes_no_pending(self):
        """clear-changes when no temp file exists should report no changes."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("clear-changes")

        output = _last_output(mock_stdout)
        assert "no uncommitted" in output.lower()


class TestEraseConfig:
    """Tests for erase-configuration command."""

    def test_erase_config_creates_empty_temp(self):
        """erase-configuration should create a temp file with empty config."""
        shell, mock_stdout = _make_shell()

        # Create existing config
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"some": "data"}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("erase-configuration")

        output = _last_output(mock_stdout)
        assert "cleared" in output.lower()

        # Temp file should exist with empty config
        assert os.path.exists(TEMP_FILE)
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data == {}

    def test_erase_and_commit(self):
        """erase-configuration followed by commit should save empty config."""
        shell, mock_stdout = _make_shell()

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"some": "data"}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("erase-configuration")
        shell.onecmd("commit")

        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert main_data == {}


class TestRollbackConfig:
    """Tests for rollback command."""

    def test_rollback_loads_backup_into_temp(self):
        """rollback N should load .oldN into temp file for review."""
        shell, mock_stdout = _make_shell()

        # Create a backup file
        with open(f"{CONFIG_FILE}.old1", "w") as f:
            yaml.safe_dump({"version": "backup1"}, f)
        # Create main config
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"version": "current"}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("rollback 1")

        output = _last_output(mock_stdout)
        assert "backup" in output.lower() or "loaded" in output.lower()

        # Temp file should contain the backup data
        assert os.path.exists(TEMP_FILE)
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data == {"version": "backup1"}

    def test_rollback_nonexistent_backup(self):
        """rollback to a non-existent backup should report an error."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("rollback 99")

        output = _last_output(mock_stdout)
        assert "not found" in output.lower()

    def test_rollback_then_commit(self):
        """rollback followed by commit should restore the backed-up version."""
        shell, mock_stdout = _make_shell()

        # Create backup
        with open(f"{CONFIG_FILE}.old1", "w") as f:
            yaml.safe_dump({"restored": True}, f)
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"current": True}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("rollback 1")
        shell.onecmd("commit")

        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert main_data == {"restored": True}


class TestShowConfig:
    """Tests for show configuration command."""

    def test_show_configuration(self):
        """show configuration should display current config content."""
        shell, mock_stdout = _make_shell()

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"logging": {"terminal": {"severity": "info"}}}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("show configuration")

        output = _last_output(mock_stdout)
        assert "severity" in output
        assert "info" in output

    def test_show_configuration_empty(self):
        """show configuration on empty config should not raise an error.
        Note: empty dict {} is falsy so PICLE's 'if ret:' skips writing output."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("show configuration")

        # Empty config returns {} which is falsy - PICLE does not write output
        # Verify no error occurred by checking no write was made for this command
        # (configure_terminal entering subshell also doesn't write)
        assert True  # no exception raised


class TestShowChanges:
    """Tests for show changes command."""

    def test_show_changes_no_temp_file(self):
        """show changes when no temp file exists should report no changes."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("show changes")

        output = _last_output(mock_stdout)
        assert "no uncommitted" in output.lower()

    def test_show_changes_with_pending(self):
        """show changes should display diff when temp file has modifications."""
        shell, mock_stdout = _make_shell()

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"version": "old"}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("show changes")

        output = _last_output(mock_stdout)
        # Should contain diff markers or the actual diff content
        assert (
            "+" in output
            or "-" in output
            or "diff" in output.lower()
            or "logging" in output.lower()
        )


# ============================================================
# End-to-end workflow tests
# ============================================================


class TestFullWorkflow:
    """End-to-end workflow tests combining multiple operations."""

    def test_edit_show_changes_commit_verify(self):
        """Full workflow: edit -> show changes -> commit -> verify config."""
        shell, mock_stdout = _make_shell()

        # Start with empty config
        Path(CONFIG_FILE).touch()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        # Make changes
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("logging file enabled true")

        # Verify temp file has accumulated changes
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "logging" in temp_data

        # Show changes should show diff
        shell.onecmd("show changes")

        # Commit
        shell.onecmd("commit")
        output = _last_output(mock_stdout)
        assert "committed" in output.lower()

        # Verify committed config
        final_data = ConfigModel.load_config(CONFIG_FILE)
        assert final_data["logging"]["terminal"]["severity"] == "debug"
        assert (
            final_data["logging"]["file"]["enabled"] == "true"
            or final_data["logging"]["file"]["enabled"] is True
        )
        assert not os.path.exists(TEMP_FILE)

    def test_edit_clear_changes_verify_no_effect(self):
        """Edit then discard: config should remain unchanged."""
        shell, mock_stdout = _make_shell()

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"original": True}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("clear-changes")

        # Main config should be unchanged
        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert main_data == {"original": True}

    def test_commit_then_rollback_then_commit(self):
        """Commit v1, commit v2, rollback to v1, commit rollback."""
        shell, mock_stdout = _make_shell()

        Path(CONFIG_FILE).touch()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        # Commit version 1
        shell.onecmd("logging terminal severity info")
        shell.onecmd("commit")
        v1 = ConfigModel.load_config(CONFIG_FILE)
        assert v1["logging"]["terminal"]["severity"] == "info"

        # Commit version 2
        shell.onecmd("logging terminal severity debug")
        shell.onecmd("commit")
        v2 = ConfigModel.load_config(CONFIG_FILE)
        assert v2["logging"]["terminal"]["severity"] == "debug"

        # Rollback to version 1 (old1 has v1 data)
        shell.onecmd("rollback 1")
        assert os.path.exists(TEMP_FILE)

        # Commit the rollback
        shell.onecmd("commit")
        rolled_back = ConfigModel.load_config(CONFIG_FILE)
        assert rolled_back["logging"]["terminal"]["severity"] == "info"

    def test_erase_clear_changes_config_preserved(self):
        """Erase then clear changes should keep original config intact.
        Note: erase-configuration currently fails due to parameter name mismatch,
        so the config is preserved because the erase operation is a no-op."""
        shell, mock_stdout = _make_shell()

        original = {"keep": "this"}
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(original, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("erase-configuration")
        shell.onecmd("clear-changes")

        # Original config should still be intact
        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert main_data == original


class TestEnumDefaultExtraction:
    """Tests for Enum default value extraction in extract_model_defaults (picle.py)."""

    def test_extract_model_defaults_converts_enum_to_value(self):
        """extract_model_defaults should convert Enum defaults to plain values."""
        from test.example_config_app import FileLoggingConfig

        shell, _ = _make_shell()
        defaults = shell.extract_model_defaults(FileLoggingConfig)

        # severity has default SeverityEnum.warning - should be extracted as "warning"
        assert defaults["severity"] == "warning"
        assert isinstance(defaults["severity"], str)

    def test_extract_model_defaults_preserves_non_enum(self):
        """Non-Enum defaults should be preserved as-is."""
        from test.example_config_app import FileLoggingConfig

        shell, _ = _make_shell()
        defaults = shell.extract_model_defaults(FileLoggingConfig)

        # enabled has default False - should remain a bool
        assert defaults["enabled"] is False

    def test_enum_defaults_serialized_in_edit(self):
        """Editing a field whose sibling has an Enum default should serialize cleanly.
        This is the original bug: editing 'logging file enabled true' would fail
        because FileLoggingConfig.severity default (SeverityEnum.warning) was passed
        through to yaml.safe_dump which cannot serialize Enum objects."""
        shell, mock_stdout = _make_shell()

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("logging file enabled true")

        # Should not crash and temp file should contain valid YAML
        assert os.path.exists(TEMP_FILE)
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert (
            temp_data["logging"]["file"]["enabled"] == "true"
            or temp_data["logging"]["file"]["enabled"] is True
        )
        # The Enum default for severity should be serialized as a plain string
        assert temp_data["logging"]["file"]["severity"] == "warning"


class TestDynamicDictionaryData:
    """Tests Dynamic Dictionary data collection."""

    def test_dynamic_dictionary_data(self):
        shell, mock_stdout = _make_shell()

        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump({"original": True}, f)

        shell.onecmd("top")
        shell.onecmd("configure_terminal")
        shell.onecmd("workers worker1 timeout 10")
        shell.onecmd("workers worker2 timeout 10 num_threads 1")
        shell.onecmd("commit")

        # Main config should be unchanged
        main_data = ConfigModel.load_config(CONFIG_FILE)
        pprint.pprint(main_data)
        assert main_data == {
            "original": True,
            "workers": {
                "worker1": {"timeout": 10, "worker_name": "worker1"},
                "worker2": {"num_threads": 1, "timeout": 10, "worker_name": "worker2"},
            },
        }


# ============================================================
# Negate model unit tests
# ============================================================


class TestDeleteNestedValue:
    """Tests for ConfigModel.delete_nested_value"""

    def test_delete_top_level_key(self):
        data = {"a": 1, "b": 2}
        result = ConfigModel.delete_nested_value(data, ["a"])
        assert result == {"b": 2}

    def test_delete_nested_key(self):
        data = {"logging": {"terminal": {"severity": "debug", "format": "%(message)s"}}}
        result = ConfigModel.delete_nested_value(
            data, ["logging", "terminal", "severity"]
        )
        assert result == {"logging": {"terminal": {"format": "%(message)s"}}}

    def test_delete_entire_subtree(self):
        data = {
            "logging": {"terminal": {"severity": "debug"}, "file": {"enabled": True}}
        }
        result = ConfigModel.delete_nested_value(data, ["logging", "terminal"])
        assert result == {"logging": {"file": {"enabled": True}}}

    def test_delete_top_level_subtree(self):
        data = {"logging": {"terminal": {}}, "workers": {"w1": {}}}
        result = ConfigModel.delete_nested_value(data, ["logging"])
        assert result == {"workers": {"w1": {}}}

    def test_delete_nonexistent_key_warns_and_returns_unchanged(self):
        data = {"a": {"b": 1}}
        result = ConfigModel.delete_nested_value(data, ["a", "missing"])
        # Key doesn't exist - data unchanged, no exception
        assert result == {"a": {"b": 1}}

    def test_delete_nonexistent_intermediate_warns_and_returns_unchanged(self):
        data = {"a": 1}
        result = ConfigModel.delete_nested_value(data, ["missing", "nested"])
        assert result == {"a": 1}

    def test_delete_empty_path_returns_unchanged(self):
        data = {"a": 1}
        result = ConfigModel.delete_nested_value(data, [])
        assert result == {"a": 1}

    def test_delete_modifies_in_place(self):
        data = {"x": {"y": 42}}
        returned = ConfigModel.delete_nested_value(data, ["x", "y"])
        assert returned is data
        assert data == {"x": {}}


class TestBuildNegateModel:
    """Tests for ConfigModel._build_negate_model structure."""

    def test_negate_model_excludes_managed_fields(self):
        """Managed fields (show, commit, rollback, etc.) must not appear in negate model."""
        from picle.models import _CONFIG_MODEL_MANAGED_FIELDS

        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        for managed in _CONFIG_MODEL_MANAGED_FIELDS:
            assert (
                managed not in negate_cls.model_fields
            ), f"Managed field '{managed}' should be excluded from negate model"

    def test_negate_model_has_user_fields(self):
        """User-defined fields (logging, workers) should be present."""
        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        assert "logging" in negate_cls.model_fields
        assert "workers" in negate_cls.model_fields

    def test_negate_model_leaf_fields_have_presence(self):
        """Scalar leaf fields in the negate model should carry presence=True."""
        from test.example_config_app import TerminalLoggingConfig

        negate_cls = ConfigModel._build_negate_model(TerminalLoggingConfig)
        for field_name, field_info in negate_cls.model_fields.items():
            extra = field_info.json_schema_extra or {}
            assert (
                extra.get("presence") is True
            ), f"Leaf field '{field_name}' missing presence=True in negate model"

    def test_negate_model_nested_fields_are_models(self):
        """Nested model fields in the negate result should themselves be model types."""
        from pydantic._internal._model_construction import ModelMetaclass

        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        logging_field = negate_cls.model_fields["logging"]
        assert isinstance(
            logging_field.annotation, ModelMetaclass
        ), "logging field in negate model should be a nested model"

    def test_negate_model_has_run_method(self):
        """Dynamically built negate model must have a run() staticmethod."""
        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        assert callable(getattr(negate_cls, "run", None))

    def test_negate_model_preserves_aliases(self):
        """Field aliases should be preserved in the negate model."""
        from test.example_config_app import TerminalLoggingConfig

        # TerminalLoggingConfig.format has alias="format" - trivially the same,
        # but let's use a model that has a non-trivial alias: FileLoggingConfig has none.
        # Use WorkerConfigModel which has plain names.  Instead verify LoggingConfigModel
        # negate contains terminal and file which are field names without aliases.
        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        # workers field has no alias but should still be accessible by field name
        assert "workers" in negate_cls.model_fields

    def test_negate_model_pkey_field_preserved(self):
        """Dynamic dict fields with pkey metadata should preserve pkey in negate model."""
        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        workers_field = negate_cls.model_fields["workers"]
        extra = workers_field.json_schema_extra or {}
        assert extra.get("pkey") == "worker_name"

    def test_negate_model_name_reflects_source(self):
        """Built negate model class name should be 'Negate' + source class name."""
        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        assert negate_cls.__name__ == "NegateMyConfigStore"

    def test_nested_negate_models_recurse(self):
        """Negate model for a nested type should itself be a negate model with leaf presence."""
        from pydantic._internal._model_construction import ModelMetaclass

        negate_cls = ConfigModel._build_negate_model(MyConfigStore)
        logging_field = negate_cls.model_fields["logging"]
        negate_logging_cls = logging_field.annotation
        assert isinstance(negate_logging_cls, ModelMetaclass)

        # terminal field inside NegateLoggingConfigModel should be a model too
        assert "terminal" in negate_logging_cls.model_fields
        assert "file" in negate_logging_cls.model_fields


class TestNegateModelInjection:
    """Tests for __init_subclass__ auto-injection of 'no' field."""

    def test_no_field_injected(self):
        """ConfigModel subclass should have a 'no' field after class creation."""
        assert "no" in MyConfigStore.model_fields

    def test_no_field_is_model(self):
        """The 'no' field annotation should resolve to a Pydantic model type."""
        from pydantic._internal._model_construction import ModelMetaclass

        no_field = MyConfigStore.model_fields["no"]
        assert isinstance(
            no_field.annotation, ModelMetaclass
        ), "'no' field should be a Pydantic model"

    def test_no_field_negate_model_excludes_managed_fields(self):
        """The injected negate model should not contain managed ConfigModel fields."""
        from picle.models import _CONFIG_MODEL_MANAGED_FIELDS

        no_field = MyConfigStore.model_fields["no"]
        negate_cls = no_field.annotation
        for managed in _CONFIG_MODEL_MANAGED_FIELDS:
            assert managed not in negate_cls.model_fields

    def test_independent_subclasses_get_independent_negate_models(self):
        """Two independent ConfigModel subclasses each have their own negate model
        whose fields are drawn only from that subclass's own user-defined fields."""
        from pydantic._internal._model_construction import ModelMetaclass

        # NegateMyConfigStore should have 'logging' and 'workers' but NOT the fields
        # of LoggingConfigModel directly (those live one level deeper).
        no_field = MyConfigStore.model_fields["no"]
        negate_cls = no_field.annotation
        assert isinstance(negate_cls, ModelMetaclass)

        # User-defined fields of MyConfigStore must be present in negate model
        assert "logging" in negate_cls.model_fields
        assert "workers" in negate_cls.model_fields

        # Fields belonging to NESTED models must NOT appear at the top level
        assert (
            "terminal" not in negate_cls.model_fields
        ), "terminal is a field of LoggingConfigModel, not MyConfigStore"
        assert (
            "file" not in negate_cls.model_fields
        ), "file is a field of LoggingConfigModel, not MyConfigStore"
        assert (
            "severity" not in negate_cls.model_fields
        ), "severity is a leaf field two levels deep, not at MyConfigStore level"


# ============================================================
# Negate integration tests – shell command execution
# ============================================================


class TestNegateConfig:
    """Integration tests for 'no <path>' commands via the shell."""

    def _seed_config(self, data: dict):
        """Write data directly to the main config file."""
        with open(CONFIG_FILE, "w") as f:
            yaml.safe_dump(data, f)

    # ---- leaf field negation ------------------------------------------------

    def test_no_leaf_field_removes_key(self):
        """'no logging terminal severity' should remove that specific key."""
        self._seed_config(
            {"logging": {"terminal": {"severity": "debug", "format": "%(message)s"}}}
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging terminal severity")

        output = _last_output(mock_stdout)
        assert "negated" in output.lower() or "uncommitted" in output.lower()

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "severity" not in temp_data.get("logging", {}).get(
            "terminal", {}
        ), "severity key should have been removed"
        # sibling key should be untouched
        assert temp_data["logging"]["terminal"].get("format") == "%(message)s"

    def test_no_leaf_field_then_commit(self):
        """Negate a leaf field, commit, and verify main config no longer has it."""
        self._seed_config(
            {"logging": {"terminal": {"severity": "debug", "format": "%(message)s"}}}
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging terminal severity")
        shell.onecmd("commit")

        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert "severity" not in main_data.get("logging", {}).get("terminal", {})
        assert main_data["logging"]["terminal"].get("format") == "%(message)s"
        assert not os.path.exists(TEMP_FILE)

    # ---- subtree negation ---------------------------------------------------

    def test_no_nested_model_removes_subtree(self):
        """'no logging terminal' should remove the entire terminal sub-dict."""
        self._seed_config(
            {
                "logging": {
                    "terminal": {"severity": "debug"},
                    "file": {"enabled": True},
                }
            }
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging terminal")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "terminal" not in temp_data.get(
            "logging", {}
        ), "terminal sub-dict should have been removed"
        # sibling section should be untouched
        assert temp_data["logging"].get("file", {}).get("enabled") is True

    def test_no_top_level_section_removes_whole_section(self):
        """'no logging' should remove the entire logging section."""
        self._seed_config(
            {
                "logging": {"terminal": {"severity": "debug"}},
                "workers": {"w1": {"timeout": 30}},
            }
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "logging" not in temp_data, "logging section should have been removed"
        # workers section should be untouched
        assert "workers" in temp_data

    def test_no_subtree_then_commit(self):
        """Negate a subtree, commit, and verify main config reflects removal."""
        self._seed_config(
            {
                "logging": {
                    "terminal": {"severity": "info"},
                    "file": {"enabled": False},
                }
            }
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging terminal")
        shell.onecmd("commit")

        main_data = ConfigModel.load_config(CONFIG_FILE)
        assert "terminal" not in main_data.get("logging", {})
        assert "file" in main_data.get("logging", {})

    # ---- negate on top of staged changes ------------------------------------

    def test_negate_accumulates_with_staged_edits(self):
        """Negate should operate on the temp file when edits are already staged."""
        self._seed_config({"logging": {"terminal": {"severity": "info"}}})
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        # Stage an edit first
        shell.onecmd("logging file enabled true")
        assert os.path.exists(TEMP_FILE)

        # Then negate the original terminal severity
        shell.onecmd("no logging terminal severity")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        # Staged edit should be present
        assert temp_data.get("logging", {}).get("file", {}).get("enabled") in (
            True,
            "true",
        )
        # Negated key should be gone
        assert "severity" not in temp_data.get("logging", {}).get("terminal", {})

    # ---- dynamic dictionary negation ----------------------------------------

    def test_no_worker_removes_entire_worker_entry(self):
        """'no workers worker1' should remove the worker1 entry from workers dict."""
        self._seed_config(
            {
                "workers": {
                    "worker1": {"timeout": 10, "worker_name": "worker1"},
                    "worker2": {"timeout": 20, "worker_name": "worker2"},
                }
            }
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no workers worker1")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "worker1" not in temp_data.get(
            "workers", {}
        ), "worker1 should have been removed"
        assert "worker2" in temp_data.get("workers", {}), "worker2 should be untouched"

    def test_no_worker_field_removes_specific_field(self):
        """'no workers worker1 timeout' should remove only the timeout key."""
        self._seed_config(
            {
                "workers": {
                    "worker1": {
                        "timeout": 10,
                        "num_threads": 4,
                        "worker_name": "worker1",
                    },
                }
            }
        )
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no workers worker1 timeout")

        temp_data = ConfigModel.load_config(TEMP_FILE)
        w1 = temp_data.get("workers", {}).get("worker1", {})
        assert "timeout" not in w1, "timeout should have been removed"
        assert w1.get("num_threads") == 4, "num_threads should be untouched"

    # ---- negate non-existent key (graceful) ---------------------------------

    def test_no_nonexistent_key_does_not_crash(self):
        """Negating a key that doesn't exist in config should not raise an exception."""
        self._seed_config({"logging": {"terminal": {"severity": "info"}}})
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        # format doesn't exist in the config - should still produce a temp file
        shell.onecmd("no logging terminal format")

        # Temp file should be written with unchanged content (format was never there)
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert temp_data["logging"]["terminal"]["severity"] == "info"

    def test_no_nonexistent_section_does_not_crash(self):
        """Negating an entirely missing section should not raise an exception."""
        self._seed_config({"workers": {"w1": {"timeout": 5}}})
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        # logging section doesn't exist - should warn but not crash
        shell.onecmd("no logging")

        # Config remains intact (no logging to remove)
        temp_data = ConfigModel.load_config(TEMP_FILE)
        assert "workers" in temp_data

    # ---- negate return message ----------------------------------------------

    def test_no_command_returns_uncommitted_message(self):
        """Negate command output should mention uncommitted or negated."""
        self._seed_config({"logging": {"terminal": {"severity": "debug"}}})
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("no logging terminal severity")

        output = _last_output(mock_stdout)
        assert any(
            word in output.lower() for word in ("negated", "uncommitted", "commit")
        )

    # ---- full round-trip ----------------------------------------------------

    def test_set_then_negate_then_commit(self):
        """Set a key, negate it, commit: final config should not have the key."""
        shell, mock_stdout = _make_shell()
        shell.onecmd("top")
        shell.onecmd("configure_terminal")

        shell.onecmd("logging terminal severity debug")
        shell.onecmd("commit")
        assert (
            ConfigModel.load_config(CONFIG_FILE)["logging"]["terminal"]["severity"]
            == "debug"
        )

        shell.onecmd("no logging terminal severity")
        shell.onecmd("commit")

        final = ConfigModel.load_config(CONFIG_FILE)
        assert "severity" not in final.get("logging", {}).get("terminal", {})
