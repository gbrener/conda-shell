"""
Entry point for conda-shell (via bin/conda-shell executable).
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import re
import subprocess
import uuid
import shlex
import copy

from .conda_cli import CondaShellCLI, CondaShellArgumentError
from .interactive import setup_env, InteractiveShell


DEFAULT_ENV_PREFIX = os.environ.get('CONDA_SHELL_ENV_PREFIX', 'shell_')


def rand_env_name(prefix=None):
    """Return a unique environment name of prefix + some hex UUID. If prefix is
    None, use DEFAULT_ENV_PREFIX.
    """
    if prefix is None:
        prefix = DEFAULT_ENV_PREFIX
    return prefix + uuid.uuid4().hex


def is_shell_env(env_dpath, prefix=None):
    """Return True if env_dpath refers to a conda environment created by
    conda-shell. Environments are identified by prefix. If prefix is None, use
    DEFAULT_ENV_PREFIX.
    """
    if prefix is None:
        prefix = DEFAULT_ENV_PREFIX
    return os.path.basename(env_dpath).startswith(prefix)


def parse_script_cmds(script_fpath, cli):
    """Return a list of argparse.Namespace objects, representing parsed
    arguments to be passed to `conda install`. Assumes that conda-shell
    is being run from inside of a shebang line.
    """
    conda_cmds = []
    interpreter = None
    with open(script_fpath, 'r') as fp:
        for line in fp:
            if re.match(r'^#!\s*conda-shell\s+', line):
                cs_cmd = shlex.split(line.split('conda-shell', 1)[1].rstrip())
                args = cli.parse_shell_args(cs_cmd)
                if args.run is not None:
                    raise CondaShellArgumentError(
                        'Please do not provide --run argument when calling'
                        ' conda-shell from the shebang line'
                    )
                if args.name is not None:
                    raise CondaShellArgumentError(
                        'Please do not provide -n/--name argument when calling'
                        ' conda-shell from the shebang line'
                    )
                if not conda_cmds and args.interpreter is None:
                    raise CondaShellArgumentError(
                        'The first "#!conda-shell" shebang line should provide'
                        ' the -i/--interactive argument. This is necessary so'
                        ' that conda-shell knows how to execute the script.'
                    )
                args._argv = cs_cmd
                if (args.interpreter is not None and
                        args.interpreter != interpreter):
                    if interpreter is not None:
                        raise CondaShellArgumentError(
                            'Conflicting -i/--interpreter arguments provided'
                            ' in different shebang lines. Please make change'
                            ' them to be equivalent, or remove all but the'
                            ' first one.'
                        )
                    interpreter = args.interpreter
                args.yes = True
                if not conda_cmds:
                    args.name = rand_env_name()
                else:
                    args.name = conda_cmds[0].name
                conda_cmds.append(args)

    if interpreter is None:
        raise CondaShellArgumentError(
            'The first "#!conda-shell" shebang line should provide the'
            ' -i/--interactive argument. This is necessary so that conda-shell'
            ' knows how to execute the script.'
        )

    # Set the --interpreter and --run arguments of each conda-shell command
    # (read in the shebang lines)
    for cs_cmd in conda_cmds:
        cs_cmd.interpreter = interpreter
        cs_cmd.run = cs_cmd.interpreter + ' ' + script_fpath

    return conda_cmds


def get_conda_env_dirs(prefix):
    """Return an iterable which yields strings representing the directory paths
    to all conda environments created by conda-shell, in descending order by
    last-modification time (recently modified come first). The `is_shell_env`
    function is used to determine whether the environment was created by
    conda-shell.
    """
    envs = os.listdir(prefix)
    env_dpaths = sorted(map(lambda env: os.path.join(prefix, env),
                            filter(is_shell_env, envs)),
                        key=lambda dpath: os.path.getmtime(dpath),
                        reverse=True)
    return env_dpaths


def env_has_pkgs(env_dpath, cmds, cli):
    """Return True if env_dpath points to a conda environment which contains
    packages requested by cmds list.

    TODO: Refactor this function so it relies on fewer "hacks".
    """
    hist_fpath = os.path.join(env_dpath, 'conda-meta', 'history')

    cmd_idx = 0
    with open(hist_fpath, 'r') as fp:
        for line in fp:
            if not line.startswith('# cmd: conda'):
                continue

            hist_ln = line.split('# cmd: ', 1)[1]
            if hist_ln.startswith('conda create'):
                hist_argv = shlex.split(hist_ln)[2:]
                hist_args = cli.parse_create_args(hist_argv)
            elif hist_ln.startswith('conda install'):
                hist_argv = shlex.split(hist_ln)[2:]
                hist_args = cli.parse_install_args(hist_argv)
            else:  # pragma: no cover
                continue

            if cmd_idx >= len(cmds):
                return False
            expected_args = cmds[cmd_idx]
            if (expected_args.packages == hist_args.packages and
                    expected_args.channel == hist_args.channel):
                cmd_idx += 1
            else:
                return False

    return cmd_idx == len(cmds)


def run_cmds_in_env(cmds, cli, argv, in_shebang=False):
    """Execute the cmds (list of argparse.Namespace objects) in a temporary
    conda environment. Interactive shell functionality is a REPL. Shebang lines
    are handled the same way we handle running arbitrary commands with --run:
    the --run parameter simply becomes "<interpreter> <script_fpath>" in the
    case of a shebang line invocation of conda-shell.
    """
    env_vars = os.environ.copy()

    # If there is an environment we can reuse, then find/activate it
    env_to_reuse = os.environ.get('CONDA_SHELL_ENV_NAME', None)
    if env_to_reuse is None:
        env_dpaths = get_conda_env_dirs(cli.prefix_dpath)
        for env_dpath in env_dpaths:
            if env_has_pkgs(env_dpath, cmds, cli):
                env_to_reuse = os.path.basename(env_dpath)
                print('Reusing shell env "{}"...'.format(env_to_reuse),
                      file=sys.stderr)
                env_vars['CONDA_SHELL_ENV_NAME'] = env_to_reuse
                break

    # Existing environment was not found, so create a fresh one.
    if env_to_reuse is None:
        print('Creating new environment "{}"...'.format(cmds[0].name),
              file=sys.stderr)
        cli.conda_create(cmds[0])
        for cmd in cmds[1:]:
            cli.conda_install(cmd)
        found_env = False
        env_dpaths = get_conda_env_dirs(cli.prefix_dpath)
        for env_dpath in env_dpaths:
            if os.path.basename(env_dpath) == cmds[0].name:
                found_env = True
                break
        if not found_env:  # pragma: no cover
            raise ValueError('Could not find freshly-created environment named'
                             ' "{}"'.format(cmds[0].name))

    env_vars = setup_env(env_vars, env_dpath)
    if cmds[0].run is not None:
        for cmd in cmds:
            if env_to_reuse is not None:
                cmd.name = env_to_reuse
        # Retain arguments from cmdline if called from a shebang
        if in_shebang:
            run_cmd = shlex.split(cmds[0].run) + argv[2:]
        else:
            run_cmd = shlex.split(cmds[0].run)
        subprocess.call(run_cmd,
                        env=env_vars,
                        universal_newlines=True)
    else:
        prompt = '[{}]: '.format(os.path.basename(env_dpath))
        InteractiveShell(prompt, env=env_vars).cmdloop()


def main(argv):
    cli = CondaShellCLI()

    in_shebang = (len(argv) > 1 and
                  argv[0].endswith('conda-shell') and
                  os.path.isfile(argv[1]) and
                  os.access(argv[1], os.X_OK))

    if in_shebang:
        script_fpath = argv[1]
        cmds = parse_script_cmds(script_fpath, cli)
    else:
        cmds = [cli.parse_shell_args(argv[1:])]
        cmds[0]._argv = copy.deepcopy(argv)
        cmds[0].yes = True
        if cmds[0].name is None:
            cmds[0].name = rand_env_name()

    run_cmds_in_env(cmds, cli, argv, in_shebang=in_shebang)
