# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status.builder import FAILURE
from main import chromium_notifier
from main import main_utils


forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

vtunejit_categories_steps = {'vtunejit': ['runhooks', 'compile']}
clusterfuzz_categories_steps = {'clusterfuzz': ['check clusterfuzz']}

class V8Notifier(chromium_notifier.ChromiumNotifier):
  def isInterestingStep(self, build_status, step_status, results):
    """Watch only failing steps."""
    return results[0] == FAILURE


def Update(config, active_main, c):
  c['status'].append(V8Notifier(
      fromaddr=active_main.from_address,
      categories_steps=vtunejit_categories_steps,
      exclusions={},
      relayhost=config.Main.smtp,
      sendToInterestedUsers=False,
      extraRecipients=['chunyang.dai@intel.com'],
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=main_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))
  c['status'].append(V8Notifier(
      fromaddr=active_main.from_address,
      categories_steps=clusterfuzz_categories_steps,
      exclusions={},
      relayhost=config.Main.smtp,
      sendToInterestedUsers=False,
      extraRecipients=[
        'v8-clusterfuzz-sheriff@chromium.org',
        'machenbach@chromium.org',
      ],
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=main_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))

