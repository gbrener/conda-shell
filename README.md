# conda-shell

Port of the [nix-shell](https://github.com/NixOS/nix) command for the [conda package manager](https://github.com/conda/conda).

**Note: `conda-shell` is still _alpha/experimental_ status, and only tested on Linux and OSX, Python 2.7/3.5/3.6. GitHub issues (bug reports, feature requests, etc) and PRs are welcome.**

## Purpose

In a nutshell (pun intended), `conda-shell` has the following goals:

- Make conda environments as "cheap" as possible to create and reuse, based on package specs rather than environment names
- Treat conda environments in a similar fashion (philosophically) to containers, i.e.
    - Enable execution of arbitrary commands in a predefined environment, or
    - Activate an environment as an interactive subshell
- Maintain feature-parity with `nix-shell`, to the extent that conda supports it

Some auxillary benefits:

- Distribute a single script (including its versioned dependencies), without creating a conda package nor an _environment.yml_ file
- Run arbitrary commands inside conda environments without doing any `source`-ing or misremembering an environment's name 
- Save some keystrokes

## Installation

Currently there is only one method of installation:
- [From source](#from-source)

Soon there will be two (via `conda install`).

### From source

Alternatively, `conda-shell` may be installed from source:

```
git clone https://github.com/gbrener/conda-shell.git
cd conda-shell
python setup.py install
```

## Usage

`conda-shell` is designed to be used in (at least) three contexts:

- [Running arbitrary commands in a conda environment](#arbitrary-commands)
- [Starting an interactive shell inside of a conda environment](#interactive-shell)
- [Using `conda-shell` inside of a script](#inside-a-script)

The following examples assume a desired environment of `Python 3.6` and `NumPy 1.13`.

### Arbitrary commands

Here we run Python code inside of the environment:

```
conda-shell python=3.6 numpy=1.13 --run 'python -c "import numpy as np; print(np.__version__)"'
```

With the same dependencies, this is how we'd run a script:

```
conda-shell python=3.6 numpy=1.13 --run 'python helloworld.py'
```

Note that the second command finds the existing environment and reuses it.

### Interactive Shell

Without the `--run` argument, an interactive shell prompt appears:

```
conda-shell python=3.6 numpy=1.13
...
### conda-shell v0.0.1.dev1
[shell_abc]: 
```

A similar effect could be acheived with the following `conda` commands:

```
conda create -n shell_abc python=3.6 numpy=1.13
source activate shell_abc
```

One advantage of using `conda-shell` here is that you wouldn't need to memorize the new environment's name; `conda-shell` would find it automatically based on the dependencies. Also, entering/exiting the `conda-shell` environment automatically activates/deactivates it, saving you some typing.

### In a script

Create a file called `np-ver-check.py`. Note the `-i` argument, indicating that the `python` program should be used to interpret the file (similar to typing `#!/usr/bin/env python`):

```
#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.13

import numpy as np

print(np.__version__)
```

Make the script executable:

```
chmod +x np-ver-check.py
```

Run it and let `conda-shell` work its magic!

```
./np-ver-check.py
```

## Misc commands

Remove all environments created by `conda-shell`:

In `bash` shell, for example:
```
for e in `conda info --envs | awk '/\/shell_/ {print $2}'`; do
  conda env remove -n `basename $e`;
done
```

## FAQ

Q: Where are the environments that `conda-shell` created? Can I remove/modify them outside of `conda-shell`?
> A: The environments are in the same location as where `conda` puts them; in fact, `conda-shell` creates those environments by calling out to `conda` as a subprocess. Conda environments created by `conda-shell` can be managed by `conda env` commands.

Q: Have you seen [conda-execute](https://github.com/conda-tools/conda-execute)?
> A: On the surface, `conda-shell` may look like it offers very similar features as `conda-execute`. However there are a number of important differences:
>    - `conda-shell` has different goals than `conda-execute` (see [above](#purpose))
>    - Syntactically, `conda-shell`'s use of the [shebang line](https://en.wikipedia.org/wiki/Shebang_(Unix)) (borrowed from `nix-shell`'s syntax) is more terse and reuses the CLI from the `conda install` command. This avoids inventing (and maintaining) a new YAML-based syntax for declaring package dependencies
>    - `conda-shell` does not need to be installed into the root environment
>    - `conda-shell` offers container-like features, such as executing arbitrary commands and acting as an interactive subshell

Q: Why is this not a part of `conda` (like `nix-shell` is a part of `nix`)?
> A: First of all, `conda-shell` is still a very immature tool. Second, `conda-shell` is not (yet?) compatible with Windows.

Q: Does this project have all the features of `nix-shell`?
> A: No. It may never reach the full functionality of `nix-shell`, since `nix` is a package manager with different ambitions than `conda`. However this is a step in that direction.
