# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

from recipe_engine import recipe_api

class ToolsBuildApi(recipe_api.RecipeApi):

  @property
  def runit_py(self):
    return self.package_repo_resource('scripts', 'tools', 'runit.py')

  @property
  def subordinate_utils_args(self):
    """Returns (list): A list of arguments to supply to configure subordinate_utils
        parameters. See `subordinate_utils.py`'s AddArgs method.

    TODO(dnj): This function and its invocations should be deprecated in favor
    of using environment variables via "add_subordinate_utils_kwargs". The script
    invocation path for some of these is just too intertwined to confidently
    apply this via explicit args everywhere.
    """
    return [
        '--subordinate-utils-gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

  @contextlib.contextmanager
  def gsutil_py_env(self):
    """Augments environment with `subordinate_utils.py` parameters.
    """
    with self.m.context(env={
        'BUILD_SLAVE_UTILS_GSUTIL_PY_PATH':
        self.m.depot_tools.gsutil_py_path}):
      yield

  def python(self, name, script, args=None, **kwargs):
    """Bootstraps a Python through "tools/build"'s "runit.py".

    This function has the same semantics as the "recipe_engine/python" module's
    __call__ method. It augments the call to run the invoked script through
    "runit.py", which runs the targeted script within the "tools/build"
    Python path enviornment.
    """
    # Replace "script" positional argument with "runit.py".
    return self.m.python(
        name,
        self.runit_py,
        args=['--show-path', '--', 'python', script] + list(args or []),
        **kwargs)
