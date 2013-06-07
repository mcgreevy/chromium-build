# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""This module contains recipe_configs_util-style configuration for
chromium recipes."""

import platform
import sys

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import DictConfig, SimpleConfig, StaticConfig
from slave.recipe_configs_util import SetConfig, BadConf


# Because of the way that we use decorators, pylint can't figure out the proper
# type signature of functions annotated with the @config_item decorator.
# pylint: disable=E1123

def norm_platform(plat=None):
  plat = plat or sys.platform
  if plat.startswith('linux'):
    return 'linux'
  elif plat.startswith(('win', 'cygwin')):
    return 'win'
  elif plat.startswith(('darwin', 'mac')):
    return 'mac'
  elif plat.startswith('ios'):
    return 'ios'
  elif plat.startswith('android'):
    return 'android'
  elif plat.startswith('chromeos'):
    return 'chromeos'
  else:  # pragma: no cover
    raise ValueError('Don\'t understand platform "%s"' % plat)


# Because norm_bits and norm_arch actually accept None as a valid parameter,
# give them a means of distinguishing when they've been passed a default
# argument v. None
HostPlatformValue = object()

def norm_bits(arch=HostPlatformValue):
  if arch is HostPlatformValue:
    arch = platform.machine()
  if not arch:
    return None
  return 64 if '64' in str(arch) else 32

def norm_arch(arch=HostPlatformValue):
  if arch is HostPlatformValue:
    arch = platform.machine()
  if not arch:
    return None

  # platform.machine() can be things like:
  #   * x86_64
  #   * i386
  #   * etc.
  # So we cheat a bit here and just look at the first char as a heruistic.
  return 'intel' if arch[0] in 'xi' else 'arm'

def norm_build_config(build_config=None):
  return 'Debug' if build_config == 'Debug' else 'Release'

# Schema for config items in this module.
def BaseConfig(HOST_PLATFORM=norm_platform(), HOST_ARCH=norm_arch(),
               HOST_BITS=norm_bits(), TARGET_PLATFORM=norm_platform(),
               TARGET_ARCH=norm_arch(), TARGET_BITS=norm_bits(),
               BUILD_CONFIG=norm_build_config()):
  return ConfigGroup(
    compile_py = ConfigGroup(
      default_targets = SetConfig(str),
      build_tool = SimpleConfig(str),
      compiler = SimpleConfig(str, required=False),
    ),
    gyp_env = ConfigGroup(
      GYP_DEFINES = DictConfig(lambda i: ('%s=%s' % i), ' '.join, (str,int)),
      GYP_GENERATORS = SetConfig(str, ','.join),
      GYP_GENERATOR_FLAGS = DictConfig(
        lambda i: ('%s=%s' % i), ' '.join, (str,int)),
      GYP_MSVS_VERSION = SimpleConfig(
        int, jsonish_fn=lambda x: (str(x) if x else ''), required=False),
    ),
    build_dir = SimpleConfig(str),

    BUILD_CONFIG = StaticConfig(norm_build_config(BUILD_CONFIG)),

    HOST_PLATFORM = StaticConfig(norm_platform(HOST_PLATFORM)),
    HOST_ARCH = StaticConfig(norm_arch(HOST_ARCH)),
    HOST_BITS = StaticConfig(norm_bits(HOST_BITS)),

    TARGET_PLATFORM = StaticConfig(norm_platform(TARGET_PLATFORM)),
    TARGET_ARCH = StaticConfig(norm_arch(TARGET_ARCH)),
    TARGET_BITS = StaticConfig(norm_bits(TARGET_BITS)),
  )

TEST_FORMAT = (
  '%(BUILD_CONFIG)s-'
  '%(HOST_PLATFORM)s.%(HOST_ARCH)s.%(HOST_BITS)s'
  '-to-'
  '%(TARGET_PLATFORM)s.%(TARGET_ARCH)s.%(TARGET_BITS)s'
)

# Used by the test harness to inspect and generate permutations for this
# config module.  {varname -> [possible values]}
VAR_TEST_MAP = {
  'HOST_PLATFORM':   ('linux', 'win', 'mac'),
  'HOST_ARCH':       ('intel',),
  'HOST_BITS':       (32, 64),

  'TARGET_PLATFORM': ('linux', 'win', 'mac', 'ios', 'android', 'chromeos'),
  'TARGET_ARCH':     ('intel', 'arm', None),
  'TARGET_BITS':     (32, 64, None),

  'BUILD_CONFIG':    ('Debug', 'Release'),
}
config_item = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_FORMAT)


@config_item(is_root=True)
def BASE(c):
  host_targ_tuples = [(c.HOST_PLATFORM, c.HOST_ARCH, c.HOST_BITS),
                      (c.TARGET_PLATFORM, c.TARGET_ARCH, c.TARGET_BITS)]

  for (plat, arch, bits) in host_targ_tuples:
    if plat in ('ios', 'android'):
      if arch or bits:
        raise BadConf('Cannot specify arch or bits for %s' % plat)
    else:
      if not (arch and bits):
        raise BadConf('"%s" requires arch and bits to be set' % plat)

    if arch == 'arm' and plat != 'chromeos':
      raise BadConf('Arm arch is only supported on chromeos')

  if c.HOST_PLATFORM not in ('win', 'linux', 'mac'):  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)

  if c.HOST_BITS < c.TARGET_BITS:
    raise BadConf('Invalid config: host bits <= targ bits')
  if c.TARGET_PLATFORM == 'ios' and c.HOST_PLATFORM != 'mac':
    raise BadConf('iOS target only supported on mac host')
  if (c.TARGET_PLATFORM in ('chromeos', 'android') and
      c.HOST_PLATFORM != 'linux'):
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))
  if c.HOST_PLATFORM in ('win', 'mac') and c.TARGET_PLATFORM != c.HOST_PLATFORM:
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))
  if c.HOST_PLATFORM == 'linux' and c.TARGET_PLATFORM in ('win', 'mac'):
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))

  if c.BUILD_CONFIG == 'Release':
    RELEASE(c)
  elif c.BUILD_CONFIG == 'Debug':
    DEBUG(c)
  else:  # pragma: no cover
    raise BadConf('Unknown build config "%s"' % c.BUILD_CONFIG)


@config_item(group='build_config_default', no_test=True)
def RELEASE(c):
  fastbuild(c, final=False)
  static_library(c, final=False)

@config_item(group='build_config_default', no_test=True)
def DEBUG(c):
  shared_library(c, final=False)
  dcheck(c, final=False)

@config_item(group='builder')
def ninja(c):
  c.gyp_env.GYP_GENERATORS.add('ninja')
  c.compile_py.build_tool = 'ninja'
  c.build_dir = 'out'

@config_item(group='builder')
def msvs(c):
  if c.HOST_PLATFORM != 'win':
    raise BadConf('can not use msvs on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('msvs')
  c.gyp_env.GYP_GENERATOR_FLAGS['msvs_error_on_missing_sources'] = 1
  c.gyp_env.GYP_MSVS_VERSION = 2010
  c.compile_py.build_tool = 'msvs'
  c.build_dir = 'out'

@config_item(group='builder')
def xcodebuild(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('can not use xcodebuild on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('xcodebuild')

@config_item(group='compiler')
def clang(c):
  c.compile_py.compiler = 'clang'

@config_item(group='compiler')
def default_compiler(_c):
  pass

@config_item(deps=['compiler', 'builder'], group='distributor')
def goma(c):
  if c.compile_py.build_tool == 'msvs':  # pragma: no cover
    raise BadConf('goma doesn\'t work with msvs')

  # TODO(iannucci): support clang and jsonclang
  if not c.compile_py.compiler:
    c.compile_py.compiler = 'goma'
  else:  # pragma: no cover
    raise BadConf('goma config dosen\'t understand %s' % c.compile_py.compiler)

  if c.TARGET_PLATFORM == 'win':
    pch(c, invert=True)

@config_item()
def pch(c, invert=False):
  if c.TARGET_PLATFORM == 'win':
    c.gyp_env.GYP_DEFINES['chromium_win_pch'] = int(not invert)

@config_item()
def dcheck(c, invert=False):
  c.gyp_env.GYP_DEFINES['dcheck_always_on'] = int(not invert)

@config_item()
def fastbuild(c, invert=False):
  c.gyp_env.GYP_DEFINES['fastbuild'] = int(not invert)

@config_item(group='link_type')
def shared_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@config_item(group='link_type')
def static_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'static_library'


#### 'Full' configurations
@config_item(includes=['ninja', 'default_compiler', 'goma'])
def chromium(c):
  c.compile_py.default_targets = ['All', 'chromium_builder_tests']

@config_item(includes=['chromium'])
def blink(c):
  c.compile_py.default_targets = ['all_webkit', 'content_shell']

