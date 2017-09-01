import os
import subprocess
import stat
import json
import time
import tempfile

import pytest
import six
from conda_shell import main, conda_cli
from .fixtures import *

if six.PY2:
    import mock
else:
    from unittest import mock


class TestMain(object):
    def test_cli_interactive(self, remove_shell_envs):
        """Test that conda-shell works as an interactive environment."""
        try:
            main.main(['conda-shell', 'python=2.7', 'numpy=1.13'])
        except (OSError, IOError) as err:
            assert 'reading from stdin' in str(err)

    def test_cli_run(self, remove_shell_envs, capfd):
        """Test that conda-shell works when running arbitrary commands."""
        main.main(
            ['conda-shell', 'python=3.5', 'numpy=1.13', '--run', 'python -V']
        )
        out, err = capfd.readouterr()
        assert 'Python 3.5' in out+err

    def test_cli_run_w_channel(self, remove_shell_envs, capfd):
        """Test that conda-shell works when running arbitrary commands, with a channel argument."""
        main.main(
            ['conda-shell', '-c', 'conda-forge', 'python=3.5', 'pydap', '--run', 'python -V']
        )
        out, err = capfd.readouterr()
        assert 'Python 3.5' in out+err

    def test_in_shebang(self, remove_shell_envs, capfd):
        """Test that conda-shell works from within a shebang line."""
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        subprocess.check_call([tempfd.name],
                              universal_newlines=True,
                              env=remove_shell_envs)
        out, err = capfd.readouterr()
        assert 'np.arange(10): [0 1 2 3 4 5 6 7 8 9]' in out+err

    def test_in_shebang_multiline(self, remove_shell_envs, capfd):
        """Test that conda-shell works from within a shebang line."""
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12
#!conda-shell -c conda-forge pandas pydap

import numpy as np
import pandas as pd
import pydap

print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        subprocess.check_call([tempfd.name],
                              universal_newlines=True,
                              env=remove_shell_envs)
        out, err = capfd.readouterr()
        assert 'np.arange(10): [0 1 2 3 4 5 6 7 8 9]' in out+err

    def test_in_shebang_mistakes(self, remove_shell_envs, capfd):
        """Test that conda-shell errors-out when called incorrectly from inside
        a shebang line:
        - No interpreter argument
        - Conflicting interpreter arguments
        - -n/--name argument provided
        - --run argument provided
        """
        # No shebang lines (need an interpreter)
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

        # No interpreter argument
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

        # Conflicting interpreter arguments
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python3 python=3.6 numpy=1.12
#!conda-shell -i python2 bzip2 gzip

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

        # -n/--name argument provided
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python -n test_env python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

        # --run argument provided
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell python=3.6 numpy=1.12 --run "print(1)"

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

        # -i and --run argument provided
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12 --run "print(1)"

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        try:
            subprocess.check_call([tempfd.name],
                                  universal_newlines=True,
                                  env=remove_shell_envs)
        except subprocess.CalledProcessError:
            assert True
        else:
            assert False

    def test_get_conda_env_dirs(self, remove_shell_envs):
        """Test that conda-shell properly identifies conda environment
        directories.
        """
        main.main(['conda-shell', 'python=2.7', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 1
        assert all(map(lambda env_dir: os.path.isdir(env_dir), env_dirs))
        assert all(map(lambda env_dir:
                       os.path.basename(env_dir).startswith(main.DEFAULT_ENV_PREFIX),
                       env_dirs))

        main.main(['conda-shell', 'python=3.5', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 2
        assert all(map(lambda env_dir: os.path.isdir(env_dir), env_dirs))
        assert all(map(lambda env_dir:
                       os.path.basename(env_dir).startswith(main.DEFAULT_ENV_PREFIX),
                       env_dirs))
        assert os.path.getmtime(env_dirs[0]) > os.path.getmtime(env_dirs[1])

        main.main(['conda-shell', 'python=3.6', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 3
        assert all(map(lambda env_dir: os.path.isdir(env_dir), env_dirs))
        assert all(map(lambda env_dir:
                       os.path.basename(env_dir).startswith(main.DEFAULT_ENV_PREFIX),
                       env_dirs))
        assert (os.path.getmtime(env_dirs[0]) >
                os.path.getmtime(env_dirs[1]) >
                os.path.getmtime(env_dirs[2]))

    def test_env_has_pkgs(self, tmp_dir):
        """Test that conda-shell properly matches environments to sets of
        packages.
        """
        env_name = 'testme_shell_a5c7c52587ad457c9d1cdc8a36e3eee8'
        env_dpath = os.path.join(tmp_dir.name, env_name)
        conda_meta_dpath = os.path.join(env_dpath, 'conda-meta')
        os.makedirs(conda_meta_dpath)
        hist_fpath = os.path.join(env_dpath, 'conda-meta', 'history')
        with open(hist_fpath, 'w') as fp:
            fp.write('''==> ABCD-EF-GH 12:34:56 <==
# cmd: conda create -n {0} python=3.6 numpy=1.12
...
==> ABCD-EF-GH 12:34:57 <==
# cmd: conda install -n {0} -c conda-forge pydap
...
'''.format(env_name))

        import argparse
        cli = conda_cli.CondaShellCLI()
        cmd1 = mock.Mock(spec=argparse.Namespace, channel=None, packages=['python=3.6', 'numpy=1.12'], _argv=['conda-shell', 'python=3.6', 'numpy=1.12'])
        cmd2 = mock.Mock(spec=argparse.Namespace, channel=['conda-forge'], packages=['pydap'], _argv=['conda-shell', '-c', 'conda-forge', 'pydap'])
        assert main.env_has_pkgs(env_dpath, [cmd1, cmd2], cli)

        cmd3 = mock.Mock(spec=argparse.Namespace, channel=None, packages=['pydap'], _argv=['conda-shell', 'pydap'])
        assert not main.env_has_pkgs(env_dpath, [cmd1, cmd3], cli)
        assert not main.env_has_pkgs(env_dpath, [cmd1], cli)
        assert not main.env_has_pkgs(env_dpath, [cmd1, cmd2, cmd3], cli)

    def test_env_reuse(self, remove_shell_envs):
        """Test that conda-shell reuses environments that already satisfy
        package dependencies.
        """
        start_tm = time.time()
        main.main(
            ['conda-shell', 'python=2.7', 'bzip2', 'pandas', '--run', 'echo']
        )
        end_tm = time.time()
        first_tdiff = end_tm - start_tm
        env_dirs_first = main.get_conda_env_dirs()
        assert len(env_dirs_first) == 1

        main.main(['conda-shell', 'python=3.5', '--run', 'echo'])
        env_dirs_second = main.get_conda_env_dirs()
        assert len(env_dirs_second) == 2

        start_tm = time.time()
        main.main(
            ['conda-shell', 'python=2.7', 'bzip2', 'pandas', '--run', 'echo']
        )
        end_tm = time.time()
        second_tdiff = end_tm - start_tm
        env_dirs_third = main.get_conda_env_dirs()
        assert env_dirs_third == env_dirs_second

        # env reuse should save us at least 5 seconds
        assert first_tdiff - second_tdiff > 5

    def test_env_reuse_multiline_shebang(self, remove_shell_envs):
        """Test that conda-shell reuses environments that already satisfy
        package dependencies.
        """
        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12
#!conda-shell -c conda-forge pydap

import pydap
import numpy as np
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        start_tm = time.time()
        subprocess.check_call([tempfd.name],
                              universal_newlines=True,
                              env=remove_shell_envs)
        end_tm = time.time()
        first_tdiff = end_tm - start_tm
        env_dirs_first = main.get_conda_env_dirs()
        assert len(env_dirs_first) == 1

        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        start_tm = time.time()
        subprocess.check_call([tempfd.name],
                              universal_newlines=True,
                              env=remove_shell_envs)
        end_tm = time.time()
        env_dirs_second = main.get_conda_env_dirs()
        assert len(env_dirs_second) == 2

        tempfd = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12
#!conda-shell -c conda-forge pydap

import pydap
import numpy as np
''')
        tempfd.flush()
        tempfd.close()
        stats = os.stat(tempfd.name)
        os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
        start_tm = time.time()
        subprocess.check_call([tempfd.name],
                              universal_newlines=True,
                              env=remove_shell_envs)
        end_tm = time.time()
        second_tdiff = end_tm - start_tm
        env_dirs_third = main.get_conda_env_dirs()
        assert env_dirs_third == env_dirs_second

        # env reuse should save us at least 5 seconds
        assert first_tdiff - second_tdiff > 5
