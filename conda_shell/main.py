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
import json

from .conda_cli import CondaShellCLI, CondaShellArgumentError
from .interactive import setup_env, InteractiveShell


DEFAULT_ENV_PREFIX = 'shell_'


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
                if not conda_cmds:
                    args._argv = ['conda', 'create'] + cs_cmd
                else:
                    args._argv = ['conda', 'install'] + cs_cmd
                if (args.interpreter is not None and
                        args.interpreter != interpreter):
                    if interpreter is not None:
                        raise CondaShellArgumentError(
                            'Conflicting -i/--interpreter arguments provided'
                            ' in different shebang lines. Please make change'
                            ' them to be equivalent, or remove all but one.'
                        )
                    interpreter = args.interpreter
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
                args.yes = True
                args.name = rand_env_name()
                conda_cmds.append(args)

    if interpreter is None:
        raise CondaShellArgumentError(
            'At least one of the shebang lines (after the first one) should'
            ' provide the -i/--interactive argument. This is necessary so that'
            ' conda-shell knows how to execute the script.'
        )

    # Set the --interpreter and --run arguments of each conda-shell command
    # (read in the shebang lines)
    for cs_cmd in conda_cmds:
        cs_cmd.interpreter = interpreter
        cs_cmd.run = cs_cmd.interpreter + ' ' + script_fpath

    return conda_cmds


def get_conda_env_dirs():
    """Return an iterable which yields strings representing the directory paths
    to all conda environments created by conda-shell, in descending order by
    last-modification time (recently modified come first). The `is_shell_env`
    function is used to determine whether the environment was created by
    conda-shell.
    """
    conda_info_cmd = ['conda', 'info', '--envs', '--json']
    envs = json.loads(subprocess.check_output(conda_info_cmd,
                                              universal_newlines=True))['envs']
    env_dpaths = sorted(filter(is_shell_env, envs),
                        key=lambda dpath: os.path.getmtime(dpath),
                        reverse=True)
    return env_dpaths


def argv_without_run(argv):
    """Temporary workaround. Return a copy of argv, but without the --run
    argument.

    This is used for the purposes of comparing history commands to conda-shell
    commands.
    """
    import copy
    retval = copy.copy(argv)
    if 'conda-shell' in argv:
        idx = retval.index('conda-shell')
        retval[idx] = 'conda'
        retval = retval[:idx+1] + ['create'] + retval[idx+1:]
    if '--run' in argv:
        idx = retval.index('--run')
        retval = retval[:idx] + retval[idx+2:]
    return retval


def env_has_pkgs(env_dpath, cmds, cli):
    """Return True if env_dpath points to a conda environment which contains
    packages requested by cmds list.
    """
    hist_fpath = os.path.join(env_dpath, 'conda-meta', 'history')

    cmd_idx = 0
    with open(hist_fpath, 'r') as fp:
        for line in fp:
            if line.startswith('# cmd: '):
                hist_argv = shlex.split(line.split('# cmd: ', 1)[1].strip())
                if cmd_idx >= len(cmds):
                    return False
                expected_argv = argv_without_run(cmds[cmd_idx]._argv)
                if expected_argv == hist_argv:
                    cmd_idx += 1
                else:
                    return False

    return True


def run_cmds_in_env(cmds, cli):
    """Execute the cmds (list of argparse.Namespace objects) in a temporary
    conda environment. Interactive shell functionality is a REPL. Shebang lines
    are handled the same way we handle running arbitrary commands with --run:
    the --run parameter simply becomes "<interpreter> <script_fpath>" in the
    case of a shebang line invocation of conda-shell.
    """
    env_vars = os.environ.copy()

    # If there is an environment we can reuse, then find/activate it
    env_to_reuse = None
    env_dpaths = get_conda_env_dirs()
    for env_dpath in env_dpaths:
        if env_has_pkgs(env_dpath, cmds, cli):
            env_to_reuse = os.path.basename(env_dpath)
            print('Reusing shell env "{}"...'.format(env_to_reuse),
                  file=sys.stderr)
            break

    # Existing environment was not found, so create a fresh one.
    if env_to_reuse is None:
        cli.conda_create(cmds[0])
        found_env = False
        env_dpaths = get_conda_env_dirs()
        for env_dpath in env_dpaths:
            if os.path.basename(env_dpath) == cmds[0].name:
                found_env = True
                break
        if not found_env:  # pragma: no cover
            raise ValueError('Could not find freshly-created environment named'
                             ' "{}"'.format(cmds[0].name))

    env_vars = setup_env(env_vars, env_dpath)
    if cmds[0].run is not None:
        for args in cmds:
            if env_to_reuse is not None:
                args.name = env_to_reuse
        subprocess.call(shlex.split(cmds[0].run) + sys.argv[2:],
                        env=env_vars,
                        universal_newlines=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr)
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
        cmds[0]._argv = argv
        cmds[0].yes = True
        if cmds[0].name is None:
            cmds[0].name = rand_env_name()

    run_cmds_in_env(cmds, cli)
