import os
import subprocess
import stat
import json
import time
from tempfile import NamedTemporaryFile

import pytest
import six
from conda_shell import main, conda_cli


@pytest.fixture
def remove_shell_envs():
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
    main.DEFAULT_ENV_PREFIX = '__testme_shell_'
    shell_envs_json = subprocess.check_output('conda info --envs --json',
                                              universal_newlines=True,
                                              shell=True)
    shell_envs = filter(lambda dpath: main.is_shell_env(dpath),
                        json.loads(shell_envs_json)['envs'])
    for env_dpath in shell_envs:
        subprocess.check_call('conda env remove -p '+env_dpath,
                              universal_newlines=True,
                              shell=True)


class TestMain(object):
    def test_main_cli_interactive(self, remove_shell_envs):
        """Test that conda-shell works as an interactive environment."""
        try:
            main.main(['conda-shell', 'python=2.7', 'numpy=1.13'])
        except (OSError, IOError) as err:
            assert 'reading from stdin' in str(err)

    def test_main_cli_run(self, remove_shell_envs, capfd):
        """Test that conda-shell works when running arbitrary commands."""
        main.main(
            ['conda-shell', 'python=3.5', 'numpy=1.13', '--run', 'python -V']
        )
        out, err = capfd.readouterr()
        assert 'Python 3.5' in out

    def test_main_in_shebang(self, remove_shell_envs, capfd):
        """Test that conda-shell works from within a shebang line."""
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            subprocess.check_call([tempfd.name], universal_newlines=True)
        out, err = capfd.readouterr()
        assert 'np.arange(10): [0 1 2 3 4 5 6 7 8 9]' in out

    def test_main_in_shebang_mistakes(self, remove_shell_envs, capfd):
        """Test that conda-shell errors-out when called incorrectly from inside
        a shebang line:
        - No interpreter argument
        - Conflicting interpreter arguments
        - -n/--name argument provided
        - --run argument provided
        """
        # No interpreter argument
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            try:
                subprocess.check_call([tempfd.name], universal_newlines=True)
            except subprocess.CalledProcessError:
                out, err = capfd.readouterr()
                assert 'CondaShellArgumentError' in err
            else:
                assert False

        # Conflicting interpreter arguments
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python3 python=3.6 numpy=1.12
#!conda-shell -i python2 bzip2 gzip

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            try:
                subprocess.check_call([tempfd.name], universal_newlines=True)
            except subprocess.CalledProcessError:
                out, err = capfd.readouterr()
                assert 'CondaShellArgumentError' in err
            else:
                assert False

        # -n/--name argument provided
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python -n test_env python=3.6 numpy=1.12

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            try:
                subprocess.check_call([tempfd.name], universal_newlines=True)
            except subprocess.CalledProcessError:
                out, err = capfd.readouterr()
                assert 'CondaShellArgumentError' in err
            else:
                assert False

        # --run argument provided
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell python=3.6 numpy=1.12 --run "print(1)"

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            try:
                subprocess.check_call([tempfd.name], universal_newlines=True)
            except subprocess.CalledProcessError:
                out, err = capfd.readouterr()
                assert 'CondaShellArgumentError' in err
            else:
                assert False

        # -i and --run argument provided
        with NamedTemporaryFile() as tempfd:
            tempfd.write('''#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.12 --run "print(1)"

import numpy as np
print(f\'np.arange(10): {np.arange(10)}\')
''')
            tempfd.flush()
            stats = os.stat(tempfd.name)
            os.chmod(tempfd.name, stats.st_mode | stat.S_IEXEC)
            try:
                subprocess.check_call([tempfd.name], universal_newlines=True)
            except subprocess.CalledProcessError:
                out, err = capfd.readouterr()
                assert 'error' in err and 'not allowed with argument' in err
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
                       os.path.basename(env_dir).startswith('__testme_shell_'),
                       env_dirs))

        main.main(['conda-shell', 'python=3.5', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 2
        assert all(map(lambda env_dir: os.path.isdir(env_dir), env_dirs))
        assert all(map(lambda env_dir:
                       os.path.basename(env_dir).startswith('__testme_shell_'),
                       env_dirs))
        assert os.path.getmtime(env_dirs[0]) > os.path.getmtime(env_dirs[1])

        main.main(['conda-shell', 'python=3.6', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 3
        assert all(map(lambda env_dir: os.path.isdir(env_dir), env_dirs))
        assert all(map(lambda env_dir:
                       os.path.basename(env_dir).startswith('__testme_shell_'),
                       env_dirs))
        assert (os.path.getmtime(env_dirs[0]) >
                os.path.getmtime(env_dirs[1]) >
                os.path.getmtime(env_dirs[2]))

    def test_env_has_pkgs(self, remove_shell_envs):
        """Test that conda-shell properly matches environments to sets of
        packages.
        """
        cli = conda_cli.CondaShellCLI()

        main.main(['conda-shell', 'python=2.7', 'numpy=1.11', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert main.env_has_pkgs(env_dirs[0], ['python=2.7', 'numpy=1.11'],
                                 cli)
        # assert main.env_has_pkgs(env_dirs[0], ['python', 'numpy'], cli)
        # ^^ this should work eventually
        assert not main.env_has_pkgs(env_dirs[0], ['python'], cli)
        assert not main.env_has_pkgs(env_dirs[0], ['numpy'], cli)

        main.main(['conda-shell', 'python=3.5', 'numpy=1.12', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert main.env_has_pkgs(env_dirs[0], ['python=3.5', 'numpy=1.12'],
                                 cli)
        # assert main.env_has_pkgs(env_dirs[0], ['python', 'numpy'], cli)
        # ^^ this should work eventually
        assert not main.env_has_pkgs(env_dirs[0], ['python'], cli)
        assert not main.env_has_pkgs(env_dirs[0], ['numpy'], cli)

        main.main(['conda-shell', 'python=3.6', 'numpy=1.13', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert main.env_has_pkgs(env_dirs[0], ['python=3.6', 'numpy=1.13'],
                                 cli)
        # assert main.env_has_pkgs(env_dirs[0], ['python', 'numpy'], cli)
        # ^^ this should work eventually
        assert not main.env_has_pkgs(env_dirs[0], ['python'], cli)
        assert not main.env_has_pkgs(env_dirs[0], ['numpy'], cli)

    def test_env_reuse(self, remove_shell_envs):
        """Test that conda-shell reuses environments that already satisfy
        package dependencies.
        """
        if six.PY2:
            start_tm = time.time()
        else:
            start_tm = time.monotonic()
        main.main(['conda-shell', 'python=2.7', '--run', 'echo'])
        if six.PY2:
            end_tm = time.time()
        else:
            end_tm = time.monotonic()
        first_tdiff = end_tm - start_tm
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 1

        main.main(['conda-shell', 'python=3.5', '--run', 'echo'])
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 2

        if six.PY2:
            start_tm = time.time()
        else:
            start_tm = time.monotonic()
        main.main(['conda-shell', 'python=2.7', '--run', 'echo'])
        if six.PY2:
            end_tm = time.time()
        else:
            end_tm = time.monotonic()
        second_tdiff = end_tm - start_tm
        env_dirs = main.get_conda_env_dirs()
        assert len(env_dirs) == 2

        # conda-shell should save us at least 3 seconds of waiting
        assert first_tdiff - second_tdiff > 3
