import unittest

from conda_shell.main import main, parse_script_cmds, get_conda_env_dirs, env_has_pkgs
import pytest


class TestMain(unittest.TestCase):
    def test_main_cli_interactive(self):
        """Test that conda-shell works as an interactive environment."""
        try:
            main(['conda-shell', 'python=2.7', 'numpy=1.13'])
        except OSError as err:
            assert 'reading from stdin' in str(err)

    def test_main_cli_run(self):
        """Test that conda-shell works when running arbitrary commands."""
        main(['conda-shell', 'python=2.7', 'numpy=1.13', '--run', 'python -V'])

    def test_main_in_shebang(self):
        """Test that conda-shell works from within a shebang line."""
        pass

    def test_get_conda_env_dirs(self):
        """Test that conda-shell properly identifies conda environment directories."""
        pass

    def test_env_has_pkgs(self):
        """Test that conda-shell properly matches environments to sets of packages."""
        pass
