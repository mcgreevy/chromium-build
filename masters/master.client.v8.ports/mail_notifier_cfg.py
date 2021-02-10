# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main.v8.v8_notifier import V8Notifier


def Update(config, active_main, c):
  c['status'].extend([
    V8Notifier(
        config,
        active_main,
        categories_steps={
          's390': [],
        },
        extraRecipients=[
          'joransiu@ca.ibm.com',
          'jyan@ca.ibm.com',
          'michael_dawson@ca.ibm.com',
          # TODO(machenbach): Remove after verifying that it works.
          'machenbach@chromium.org',
        ],
    ),
    V8Notifier(
        config,
        active_main,
        categories_steps={
          'x87': [],
        },
        extraRecipients=[
          'weiliang.lin@intel.com',
          'chunyang.dai@intel.com',
          'zhengxing.li@intel.com',
          # TODO(machenbach): Remove after verifying that it works.
          'machenbach@chromium.org',
        ],
    ),
  ])
