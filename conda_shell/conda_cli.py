"""
Wrap portions of conda's command-line interface.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import importlib
import argparse
import copy

import six


class CondaShellArgumentError(Exception):
    pass


class CondaCLI(object):
    """Python wrapper for conda's command line interface.
    This enables us to call `conda` without using subprocess.

    It also offers conveniences such as modifying the argparse help output,
    and modifying the CLI as needed for conda-shell.

    Limitations:
        - current only supports 'conda install' and 'conda create'
    """

    def __init__(self):
        """Constructor."""
        # Extend sys.path so that conda.cli module can be imported, then import
        # conda's CLI modules.
        conda_sp_dpath = self._get_conda_sp_dpath()
        sys.path.append(conda_sp_dpath)
        (self._main_mod,
         self._main_install_mod,
         self._main_create_mod) = self._import_conda_modules()

        self._create_parser, self._install_parser = None, None
        parser, sub_parsers = self._main_mod.generate_parser()
        self._main_install_mod.configure_parser(sub_parsers)
        self._main_create_mod.configure_parser(sub_parsers)

        subparsers_action = None
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        action_parser_map = subparsers_action._name_parser_map
        if 'install' in action_parser_map:
            self._install_parser = action_parser_map['install']
            # The following lines are stubbed out for now, since conda does not
            # seem to like being called from a separate program.
            # These arguments are not present in the argparse Namespaces
            # self._install_parser.add_argument('--no-default-packages',
            #                                   default=False)
            # self._install_parser.add_argument('--clone', default=False)
        if 'create' in action_parser_map:
            self._create_parser = action_parser_map['create']
        # Additional branches may be added here to support more of conda's
        # subparsers

    def _get_conda_sp_dpath(self):
        """Return the site-packages directory where conda resides.
        Errors-out if the user isn't using Python from within conda.
        """
        if 'conda' not in sys.executable:
            raise ValueError('Failed to find directory where conda is'
                             ' installed. conda-shell expects to find conda'
                             ' installed in a directory with "conda" in the'
                             ' name.')

        conda_install_dpath = sys.executable.split('conda')[0] + 'conda'
        conda_sp_dpath = None
        installed_libs = os.path.join(conda_install_dpath, 'lib')
        for root, dirnames, filenames in os.walk(installed_libs, topdown=True):
            idx = 0
            while idx < len(dirnames):
                dirname = dirnames[idx]
                if not (dirname.startswith('python') or
                        dirname == 'site-packages'):
                    if root.endswith('site-packages') and dirname == 'conda':
                        conda_sp_dpath = root
                        break
                    dirnames.remove(dirname)
                    idx -= 1
                idx += 1
            if conda_sp_dpath is not None:
                break
        if conda_sp_dpath is None:
            raise ValueError('Failed to find site-packages directory where'
                             ' conda is installed.')

        return conda_sp_dpath

    def _import_conda_modules(self):
        """Import the necessary conda.cli modules. This method assumes that
        conda is available in sys.path. If it isn't, we need to call
        self._add_conda_to_syspath().
        """
        # Trick conda.cli into importing; I really wish this wasn't necessary
        if six.PY2:
            import mock
        else:
            from unittest import mock
        for modname in ['ruamel', 'ruamel.yaml', 'ruamel.yaml.comments',
                        'ruamel.yaml.scanner', 'pycosat']:
            sys.modules[modname] = mock.MagicMock()
        imported_modules = (
            importlib.import_module('conda.cli.main'),
            importlib.import_module('conda.cli.main_install'),
            importlib.import_module('conda.cli.main_create'),
        )
        return imported_modules

    def parse_create_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda create` were called over the command line.
        """
        return self._create_parser.parse_args(argv)

    def parse_install_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda install` were called over the command
        line.
        """
        return self._install_parser.parse_args(argv)

    def conda_create(self, args):  # pragma: no cover
        """Given a Namespace object from `conda create`'s argument parser,
        return the output from the `conda create` command (this may be `None`).

        This is not currently working, due to missing dependencies of conda
        (resulting in `ImportError`s).
        """
        return self._main_create_mod.execute(args, self._create_parser)

    def conda_install(self, args):  # pragma: no cover
        """Given a Namespace object from `conda install`'s argument parser,
        return the output from the `conda install` command (this may be
        `None`).

        This is not currently working, due to conda getting confused about the
        environment name (using the active env instead of the `-n` argument).
        """
        return self._main_install_mod.execute(args, self._install_parser)


class CondaShellCLI(CondaCLI):
    """Reuse conda's CLI, but modify as needed for conda-shell's purposes.

    Besides modifying the `--help` output, this adds the following arguments:
        - `--run`: For running arbitrary commands in conda environments made by
          conda-shell
        - `-i` / `--interpreter`: For providing an interpreter via a shebang
          line
    """

    def __init__(self):
        super(CondaShellCLI, self).__init__()

        # Modify --help output
        self._shell_parser = copy.copy(self._install_parser)
        self._shell_parser.prog = 'conda-shell'
        self._shell_parser.epilog = """Examples:
    conda-shell python=3.6 numpy=1.13
    conda-shell python=2.7 --run 'python -V'
"""
        self._shell_parser.description = """Port of the `nix-shell` command for the conda package manager.

This is a superset of the command-line interface for
`conda install`; execute `conda install --help` for more information.
"""
        # Create additional arguments for conda-shell
        mux_group = self._shell_parser.add_mutually_exclusive_group()
        mux_group.add_argument('--run', type=str,
                               help='Command to run inside of the temporary'
                                    'conda environment')
        mux_group.add_argument('-i', '--interpreter', type=str,
                               help='')

    def parse_shell_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda-shell` were called over the command line.
        """
        return self._shell_parser.parse_args(argv)
