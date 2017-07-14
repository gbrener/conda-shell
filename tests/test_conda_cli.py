import unittest

from conda_shell.conda_cli import CondaShellCLI


class TestCondaShellCLI(unittest.TestCase):
    def test_conda_shell_cli_call_init(self):
        """Test that CondaShellCLI class can be initialized."""
        cli = CondaShellCLI()

    def test_cs_cli_parse_create_args(self):
        """Verify that a CondaCLI instance properly parses 'conda create' commands."""
        pass

    def test_cs_cli_parse_install_args(self):
        """Verify that a CondaCLI instance properly parses 'conda install' commands."""
        pass

    def test_cs_cli_parse_shell_args(self):
        """Verify that a CondaCLI instance properly parses 'conda-shell' commands."""
        pass

    def test_cs_cli_conda_install(self):
        """Verify that a CondaCLI instance can execute 'conda install' commands."""
        pass

    @unittest.skip('Failing due to import errors')
    def test_cs_cli_conda_create(self):
        """Verify that a CondaCLI instance can execute 'conda create' commands."""
        pass
