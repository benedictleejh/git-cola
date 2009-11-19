"""Provides commands and queries for Git."""
import os

import cola
from cola import core
from cola import utils


def default_remote():
    """Return the remote tracked by the current branch."""
    branch = current_branch()
    branchconfig = 'branch.%s.remote' % branch
    model = cola.model()
    return model.local_config(branchconfig, 'origin')


def corresponding_remote_ref():
    """Return the remote branch tracked by the current branch."""
    remote = default_remote()
    branch = current_branch()
    best_match = '%s/%s' % (remote, branch)
    remote_branches = branch_list(remote=True)
    if not remote_branches:
        return remote
    for rb in remote_branches:
        if rb == best_match:
            return rb
    if remote_branches:
        return remote_branches[0]
    return remote


def diff_filenames(arg):
    """Return a list of filenames that have been modified"""
    model = cola.model()
    diff_zstr = model.git.diff(arg, name_only=True, z=True).rstrip('\0')
    return [core.decode(f) for f in diff_zstr.split('\0') if f]


def all_files():
    """Return the names of all files in the repository"""
    model = cola.model()
    return [core.decode(f)
            for f in model.git.ls_files(z=True)
                              .strip('\0').split('\0') if f]


class _current_branch:
    """Stat cache for current_branch()."""
    st_mtime = 0
    value = None


def current_branch():
    """Find the current branch."""
    model = cola.model()
    head = os.path.abspath(model.git_repo_path('HEAD'))

    try:
        st = os.stat(head)
        if _current_branch.st_mtime == st.st_mtime:
            return _current_branch.value
    except OSError, e:
        pass

    # Handle legacy .git/HEAD symlinks
    if os.path.islink(head):
        refs_heads = os.path.realpath(model.git_repo_path('refs', 'heads'))
        path = os.path.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            value = path[len(refs_heads)+1:]
            _current_branch.value = value
            _current_branch.st_mtime = st.st_mtime
            return value
        return ''

    # Handle the common .git/HEAD "ref: refs/heads/master" file
    if os.path.isfile(head):
        value = utils.slurp(head).strip()
        ref_prefix = 'ref: refs/heads/'
        if value.startswith(ref_prefix):
            value = value[len(ref_prefix):]

        _current_branch.st_mtime = st.st_mtime
        _current_branch.value = value
        return value

    # This shouldn't happen
    return ''


def branch_list(remote=False):
    """
    Return a list of local or remote branches

    This explicitly removes HEAD from the list of remote branches.

    """
    model = cola.model()
    if remote:
        refs = 'refs/remotes/'
    else:
        refs = 'refs/heads/'
    lrefs = len(refs)

    output = model.git.for_each_ref(refs, format='%(refname)').splitlines()
    noprefix = map(lambda x: x[len(refs):], output)
    return filter(lambda x: x and x != 'HEAD', noprefix)
