"""
Entry point for conda-shell (via bin/conda-shell executable).
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import re
import subprocess
import uuid
import shlex
import json

from . import __version__
from .conda_cli import CondaShellCLI
from .interactive import setup_env, InteractiveShell


def rand_env_name(prefix='shell_'):
    """Return a unique environment name of prefix + some hex UUID."""
    return prefix + uuid.uuid4().hex

def is_shell_env(env_dpath):
    """Return True if env_dpath refers to a conda environment created by conda-shell.
    """
    return os.path.basename(env_dpath).startswith('shell_')

def parse_script_cmds(script_fpath, cli):
    """Return a list of argparse.Namespace objects, representing parsed
    arguments to be passed to `conda install`. Assumes that conda-shell is being
    run from inside of a shebang line.
    """
    conda_installs = []
    interpreter = None
    with open(script_fpath, 'r') as fp:
        for linect, line in enumerate(fp):
            if linect == 0:
                continue
            elif re.match(r'^#!\s*conda-shell\s+', line):
                args = cli.parse_install_args(shlex.split(line.split('conda-shell', 1)[1].rstrip()))
                if args.interpreter != interpreter:
                    if interpreter is not None:
                        raise ValueError('Conflicting -i/--interpreter arguments provided in different shebang lines. Please make change them to be equivalent, or remove all but one.')
                    interpreter = args.interpreter
                if args.run is not None:
                    raise ValueError('Please do not provide --run argument when calling conda-shell from the shebang line')
                if args.name is not None:
                    raise ValueError('Please do not provide -n/--name argument when calling conda-shell from the shebang line')
                args.yes = True
                args.name = rand_env_name()
                conda_installs.append(args)
            else:
                break

    if interpreter is None:
        raise ValueError('At least one of the shebang lines (after the first one) should provide the -i/--interactive argument. This is necessary so that conda-shell knows how to execute the script.')

    # Set the --interpreter and --run arguments of each conda-shell command (read in the shebang lines)
    for cs_cmd in conda_installs:
        cs_cmd.interpreter = interpreter
        cs_cmd.run = cs_cmd.interpreter + ' ' + script_fpath

    return conda_installs


def get_conda_env_dirs():
    # Sort envs that starts with "shell_" by last-modified time,
    # and return the first one (if any) that match the pkg specs
    conda_info_cmd = ['conda', 'info', '--envs', '--json']
    envs = json.loads(subprocess.check_output(conda_info_cmd,
                                              universal_newlines=True))['envs']
    env_dpaths = sorted(filter(is_shell_env, envs),
                        key=lambda dpath: os.path.getmtime(dpath))
    return env_dpaths


def env_has_pkgs(env_dpath, pkgs, cli):
    """Return True if env_dpath points to a conda environment which contains
    packages described by pkgs list.
    """
    install_cmdline = 'conda install '+' '.join(pkgs)
    hist_fpath = os.path.join(env_dpath, 'conda-meta', 'history')

    hist_pkgs = set()
    # Get the packages from the 'conda create' and 'conda install' commands,
    # but immediately return False if we see additional conda commands
    # afterward.
    with open(hist_fpath, 'r') as fp:
        for line in fp:
            if line.startswith('# cmd: '):
                line = line.split('# cmd: ', 1)[1]
                if 'conda create' in line:
                    args = cli.parse_create_args(line.split()[2:])
                    hist_pkgs.update(args.packages)
                elif 'conda install' in line:
                    args = cli.parse_install_args(line.split()[2:])
                    hist_pkgs.update(args.packages)
                else:
                    return False

    return set(pkgs) == hist_pkgs


def run_cmds_in_env(cmds, cli):
    """Execute the cmds (argparse.Namespace objects) in a temporary conda
    environment. Interactive shell functionality is a REPL. Shebang lines are
    handled the same way we handle running arbitrary commands with --run:
    the --run parameter simply becomes "<interpreter> <script_fpath>" in the
    case of a shebang line invocation of conda-shell.
    """
    env_vars = os.environ.copy()

    all_pkgs = []
    for args in cmds:
        all_pkgs.extend(args.packages)

    # If there is an environment we can reuse, then find/activate it
    env_to_reuse = None
    env_dpaths = get_conda_env_dirs()
    for env_dpath in env_dpaths:
        if env_has_pkgs(env_dpath, all_pkgs, cli):
            env_to_reuse = os.path.basename(env_dpath)
            print('Reusing shell env "{}"...'.format(env_to_reuse))
            break

    # Existing environment was not found, so create a fresh one.
    if env_to_reuse is None:
        # TODO: The following lines (should) make this work without subprocess
        #cmds[0].no_default_packages = False
        #cmds[0].clone = False
        #cli.conda_create(cmds[0])
        subprocess.check_call(['conda', 'create', '-n', cmds[0].name, '-y'] + cmds[0].packages,
                              universal_newlines=True)
        found_env = False
        env_dpaths = get_conda_env_dirs()
        for env_dpath in env_dpaths:
            if os.path.basename(env_dpath) == cmds[0].name:
                found_env = True
                break
        if not found_env:
            raise ValueError('Could not find freshly-created environment named "{}'
                             '"'.format(cmds[0].name))

    env_vars = setup_env(env_vars, env_dpath)
    if cmds[0].run is not None:
        for args in cmds:
            if env_to_reuse is not None:
                args.name = env_to_reuse
        subprocess.check_call(shlex.split(cmds[0].run),
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
        cmds[0].yes = True
        if cmds[0].name is None:
            cmds[0].name = rand_env_name()

    run_cmds_in_env(cmds, cli)
