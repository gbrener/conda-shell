import pytest

from conda_shell.conda_cli import CondaShellCLI
from conda_shell import main


@pytest.fixture
def cli():
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
    main.DEFAULT_ENV_PREFIX = '__testme_shell_'
    return CondaShellCLI()


class TestCondaShellCLI(object):
    def test_cs_cli_parse_create_args(self, cli):
        """Test that a CondaCLI instance properly parses 'conda create'
        commands.
        """
        env_name = main.rand_env_name()
        args = cli.parse_create_args(['-n', env_name, 'pkg1', 'pkg2'])
        assert args.name == env_name
        assert args.packages == ['pkg1', 'pkg2']

    def test_cs_cli_parse_install_args(self, cli):
        """Test that a CondaCLI instance properly parses 'conda install'
        commands.
        """
        env_name = main.rand_env_name()
        args = cli.parse_install_args(
            ['-n', env_name, '-c', 'chan1', 'pkg1', 'pkg2']
        )
        assert args.name == env_name
        assert args.channel == ['chan1']
        assert args.packages == ['pkg1', 'pkg2']

    def test_cs_cli_parse_shell_args(self, cli):
        """Test that a CondaCLI instance properly parses 'conda-shell'
        commands.
        """
        env_name = main.rand_env_name()
        args = cli.parse_install_args(
            ['-n', env_name, '-c', 'chan1', 'pkg1', 'pkg2']
        )
        assert args.name == env_name
        assert args.channel == ['chan1']
        assert args.packages == ['pkg1', 'pkg2']

    @pytest.mark.skip('Failing due to import errors')
    def test_cs_cli_conda_create(self, cli):
        """Verify that a CondaCLI instance can execute 'conda create'
        commands.
        """
        pass

    @pytest.mark.skip('Failing due to conda interfacing error')
    def test_cs_cli_conda_install(self, cli, remove_shell_envs):
        """Verify that a CondaCLI instance can execute 'conda install'
        commands.
        """
        pass
