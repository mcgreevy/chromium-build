# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import sys

import manual_bisect_files
from recipe_engine import recipe_api


# Regular expression to identify a Git hash.
GIT_COMMIT_HASH_RE = re.compile(r'[a-zA-Z0-9]{40}')
# The Google Storage metadata key for the full commit position.
GS_COMMIT_POSITION_KEY = 'Cr-Commit-Position'
# The Google Storage metadata key for the commit position number.
GS_COMMIT_POSITION_NUMBER_KEY = 'Cr-Commit-Position-Number'
# The Google Storage metadata key for the Git commit hash.
GS_GIT_COMMIT_KEY = 'Cr-Git-Commit'


class ArchiveApi(recipe_api.RecipeApi):
  """Chromium specific module for zipping, uploading and downloading build
  artifacts implemented as a wrapper around zip_build.py script.

  If you need to upload or download build artifacts (or any other files) for
  something other than Chromium flavor, consider using 'zip' + 'gsutil' or
  'isolate' modules instead.
  """
  def zip_and_upload_build(
      self, step_name, target, build_url=None, src_dir=None,
      build_revision=None, cros_board=None, package_dsym_files=False,
      exclude_files=None, exclude_perf_test_files=False,
      update_properties=None, store_by_hash=True,
      platform=None, **kwargs):
    """Returns a step invoking zip_build.py to zip up a Chromium build.
       If build_url is specified, also uploads the build."""
    if not src_dir:
      src_dir = self.m.path['checkout']
    args = [
        '--target', target,
        '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
        '--staging-dir', self.m.path['cache'].join('chrome_staging'),
        '--src-dir', src_dir,
    ]
    args += self.m.build.slave_utils_args
    if 'build_archive_url' in self.m.properties:
      args.extend(['--use-build-url-name', '--build-url',
                   self.m.properties['build_archive_url']])
    elif build_url:
      args.extend(['--build-url', build_url])
    if build_revision:
      args.extend(['--build_revision', build_revision])
    if cros_board:
      args.extend(['--cros-board', cros_board])
    if package_dsym_files:
      args.append('--package-dsym-files')
    if exclude_files:
      args.extend(['--exclude-files', exclude_files])
    if 'gs_acl' in self.m.properties:
      args.extend(['--gs-acl', self.m.properties['gs_acl']])
    if exclude_perf_test_files and platform:
      include_bisect_file_list = (
        manual_bisect_files.CHROME_REQUIRED_FILES.get(platform))
      include_bisect_strip_list = (
        manual_bisect_files.CHROME_STRIP_LIST.get(platform))
      include_bisect_whitelist = (
        manual_bisect_files.CHROME_WHITELIST_FILES.get(platform))
      if include_bisect_file_list:
        inclusions = ','.join(include_bisect_file_list)
        args.extend(['--include-files', inclusions])
      if include_bisect_strip_list:
        strip_files = ','.join(include_bisect_strip_list)
        args.extend(['--strip-files', strip_files])
      if include_bisect_whitelist:
        args.extend(['--whitelist', include_bisect_whitelist])
      args.extend(['--exclude-extra'])

      # If update_properties is passed in and store_by_hash is False,
      # we store it with commit position number instead of a hash
      if update_properties and not store_by_hash:
        commit_position = self._get_commit_position(
                            update_properties, None)
        cp_branch, cp_number = self.m.commit_position.parse(commit_position)
        args.extend(['--build_revision', cp_number])

    properties_json = self.m.json.dumps(self.m.properties.legacy())
    args.extend(['--factory-properties', properties_json,
                 '--build-properties', properties_json])

    kwargs['allow_subannotations'] = True
    self.m.build.python(
      step_name,
      self.package_repo_resource('scripts', 'slave', 'zip_build.py'),
      args,
      infra_step=True,
      **kwargs
    )

  def _get_commit_position(self, update_properties, primary_project):
    """Returns the commit position of the project (or the specified primary
    project).
    """
    if primary_project:
      key = 'got_%s_revision_cp' % primary_project
    else:
      key = 'got_revision_cp'
    return update_properties[key]

  def _get_git_commit(self, update_properties, primary_project):
    """Returns: (str/None) the git commit hash for a given project.

    Attempts to identify the git commit hash for a given project. If
    'primary_project' is None, or if there is no git commit hash for the
    specified primary project, the checkout-wide commit hash will be used.

    If none of the candidate configurations are present, the value None will be
    returned.
    """
    if primary_project:
      commit = update_properties.get('got_%s_revision_git' % primary_project)
      if commit:
        return commit
      commit = update_properties.get('got_%s_revision' % primary_project)
      if commit and GIT_COMMIT_HASH_RE.match(commit):
        return commit

    commit = update_properties.get('got_revision_git')
    if commit:
      return commit
    commit = update_properties.get('got_revision')
    if commit and GIT_COMMIT_HASH_RE.match(commit):
      return commit
    return None

  def _get_comparable_upload_path_for_sort_key(self, branch, number):
    """Returns a sortable string corresponding to the commit position."""
    if branch and branch != 'refs/heads/master':
      branch = branch.replace('/', '_')
      return '%s-%s' % (branch, number)
    return str(number)

  def clusterfuzz_archive(
      self, build_dir, update_properties, gs_bucket,
      archive_prefix, archive_subdir_suffix='', gs_acl=None,
      revision_dir=None, primary_project=None, **kwargs):
    # TODO(machenbach): Merge revision_dir and primary_project. The
    # revision_dir is only used for building the archive name while the
    # primary_project is authoritative for the commit position.
    """Archives and uploads a build to google storage.

    The build is filtered by a list of file exclusions and then zipped. It is
    uploaded to google storage with some metadata about the commit position
    and revision attached. The zip file follows the naming pattern used by
    clusterfuzz. The file pattern is:
    <archive name>-<platform>-<target><optional component>-<sort-key>.zip

    Example: cool-project-linux-release-refs_heads_b1-12345.zip
    The archive name is "cool-project" and there's no component build. The
    commit is on a branch called b1 at commit position number 12345.

    Example: cool-project-mac-debug-x10-component-234.zip
    The archive name is "cool-project" and the component's name is "x10". The
    component is checked out in branch master with commit position number 234.

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
      update_properties: The properties from the bot_update step (containing
                         commit information)
      gs_bucket: Name of the google storage bucket to upload to
      archive_prefix: Prefix of the archive zip file
      archive_subdir_suffix: Optional suffix to the google storage subdirectory
                             name that contains the archive files
      gs_acl: ACL used for the file on google storage
      revision_dir: Optional component name if the main revision for this
                    archive is a component revision
      primary_project: Optional project name for specifying the revision of the
                       checkout
    """
    target = self.m.path.split(build_dir)[-1]
    commit_position = self._get_commit_position(
        update_properties, primary_project)
    cp_branch, cp_number = self.m.commit_position.parse(commit_position)
    build_git_commit = self._get_git_commit(update_properties, primary_project)
    staging_dir = self.m.path.mkdtemp('chrome_staging')

    llvm_tools_to_copy = ['llvm-symbolizer', 'sancov']
    llvm_bin_dir = self.m.path['checkout'].join('third_party', 'llvm-build',
                                                'Release+Asserts', 'bin')
    ext = '.exe' if self.m.platform.is_win else ''

    for tool in llvm_tools_to_copy:
      tool_src = self.m.path.join(llvm_bin_dir, tool + ext)
      tool_dst = self.m.path.join(build_dir, tool + ext)

      if not self.m.path.exists(tool_src):
        continue

      try:
        self.m.file.copy('Copy ' + tool, tool_src, tool_dst)
      except self.m.step.StepFailure:  # pragma: no cover
        # On some builds, it appears that a soft/hard link of llvm-symbolizer
        # exists in the build directory, which causes shutil.copy to raise an
        # exception. Either way, this shouldn't cause the whole build to fail.
        pass

    # Build the list of files to archive.
    filter_result = self.m.python(
        'filter build_dir',
        self.resource('filter_build_files.py'),
        [
          '--dir', build_dir,
          '--platform', self.m.platform.name,
          '--output', self.m.json.output(),
        ],
        infra_step=True,
        step_test_data=lambda: self.m.json.test_api.output(['file1', 'file2']),
        **kwargs
    )

    zip_file_list = filter_result.json.output

    # Use the legacy platform name as Clusterfuzz has some expectations on
    # this (it only affects Windows, where it replace 'win' by 'win32').
    pieces = [self.legacy_platform_name(), target.lower()]
    if archive_subdir_suffix:
      pieces.append(archive_subdir_suffix)
    subdir = '-'.join(pieces)

    # Components like v8 get a <name>-v8-component-<revision> infix.
    component = ''
    if revision_dir:
      component = '-%s-component' % revision_dir

    sortkey_path = self._get_comparable_upload_path_for_sort_key(
        cp_branch, cp_number)
    zip_file_base_name = '%s-%s-%s%s-%s' % (archive_prefix,
                                            self.legacy_platform_name(),
                                            target.lower(),
                                            component,
                                            sortkey_path)
    zip_file_name = '%s.zip' % zip_file_base_name

    self.m.python(
        'zipping',
        self.resource('zip_archive.py'),
        [
          staging_dir,
          zip_file_base_name,
          self.m.json.input(zip_file_list),
          build_dir,
        ],
        infra_step=True,
        **kwargs
    )

    zip_file = staging_dir.join(zip_file_name)

    gs_metadata = {
      GS_COMMIT_POSITION_NUMBER_KEY: cp_number,
    }
    if commit_position:
      gs_metadata[GS_COMMIT_POSITION_KEY] = commit_position
    if build_git_commit:
      gs_metadata[GS_GIT_COMMIT_KEY] = build_git_commit

    gs_args = []
    if gs_acl:
      gs_args.extend(['-a', gs_acl])
    self.m.gsutil.upload(
        zip_file,
        gs_bucket,
        "/".join([subdir, zip_file_name]),
        args=gs_args,
        metadata=gs_metadata,
        use_retry_wrapper=False,
    )
    self.m.file.remove(zip_file_name, zip_file)

  def download_and_unzip_build(
      self, step_name, target, build_url, src_dir=None,
      build_revision=None, build_archive_url=None, **kwargs):
    """Returns a step invoking extract_build.py to download and unzip
       a Chromium build."""
    if not src_dir:
      src_dir = self.m.path['checkout']
    args = [
        '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
        '--target', target,
        '--src-dir', src_dir,
    ]
    args += self.m.build.slave_utils_args
    if build_archive_url:
      args.extend(['--build-archive-url', build_archive_url])
    else:
      args.extend(['--build-url', build_url])
      if build_revision:
        args.extend(['--build_revision', build_revision])

    properties = (
      ('mastername', '--master-name'),
      ('buildnumber', '--build-number'),
      ('parent_builddir', '--parent-build-dir'),
      ('parentname', '--parent-builder-name'),
      ('parentslavename', '--parent-slave-name'),
      ('parent_buildnumber', '--parent-build-number'),
      ('webkit_dir', '--webkit-dir'),
      ('revision_dir', '--revision-dir'),
    )
    for property_name, switch_name in properties:
      if self.m.properties.get(property_name):
        args.extend([switch_name, self.m.properties[property_name]])

    # TODO(phajdan.jr): Always halt on missing build.
    if self.m.properties.get('halt_on_missing_build'):  # pragma: no cover
      args.append('--halt-on-missing-build')

    self.m.build.python(
      step_name,
      self.package_repo_resource('scripts', 'slave', 'extract_build.py'),
      args,
      infra_step=True,
      **kwargs
    )

  def legacy_platform_name(self):
    """Replicates the behavior of PlatformName() in chromium_utils.py."""
    if self.m.platform.is_win:
      return 'win32'
    return self.m.platform.name

  def _legacy_url(self, is_download, gs_bucket_name, extra_url_components):
    """Computes a build_url suitable for uploading a zipped Chromium
    build to Google Storage.

    The reason this is named 'legacy' is that there are a large number
    of dependencies on the exact form of this URL. The combination of
    zip_build.py, extract_build.py, slave_utils.py, and runtest.py
    require that:

    * The platform name be exactly one of 'win32', 'mac', or 'linux'
    * The upload URL only name the directory on GS into which the
      build goes (zip_build.py computes the name of the file)
    * The download URL contain the unversioned name of the zip archive
    * The revision on the builder and tester machines be exactly the
      same

    There were too many dependencies to tease apart initially, so this
    function simply emulates the form of the URL computed by the
    underlying scripts.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL."""

    result = ('gs://' + gs_bucket_name)
    if extra_url_components:
      result += ('/' + extra_url_components)
    if is_download:
      result += ('/' + self.m.properties['parent_buildername'] + '/' +
                 'full-build-' + self.legacy_platform_name() +
                 '.zip')
    else:
      result += '/' + self.m.properties['buildername']
    return result

  def legacy_upload_url(self, gs_bucket_name, extra_url_components=None):
    """Returns a url suitable for uploading a Chromium build to Google
    Storage.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL."""
    return self._legacy_url(False, gs_bucket_name, extra_url_components)

  def legacy_download_url(self, gs_bucket_name, extra_url_components=None):
    """Returns a url suitable for downloading a Chromium build from
    Google Storage.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL."""
    return self._legacy_url(True, gs_bucket_name, extra_url_components)
