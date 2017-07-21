import subprocess
import os

import pytest
from conda_shell import main
from .fixtures import remove_shell_envs, cli


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

    def test_cs_cli_conda_create(self, remove_shell_envs, cli):
        """Verify that a CondaCLI instance can execute 'conda create'
        commands.
        """
        env_name = main.rand_env_name()
        args = cli.parse_create_args(['-n', env_name, '-y', 'python=2.7', 'numpy=1.12'])
        cli.conda_create(args)
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 1
        assert os.path.basename(env_dirs[0]) == env_name

    def test_cs_cli_conda_install(self, remove_shell_envs, cli):
        """Verify that a CondaCLI instance can execute 'conda install'
        commands.
        """
        env_name = main.rand_env_name()
        create_args = cli.parse_create_args(['-n', env_name, '-y', 'python=2.7'])
        cli.conda_create(create_args)
        install_args = cli.parse_install_args(
            ['-n', env_name, '-c', 'chan1', '-y', 'numpy=1.12']
        )
        cli.conda_install(install_args)
        output = subprocess.check_output('conda list -n '+env_name, universal_newlines=True, shell=True)
        assert 'numpy' in output
