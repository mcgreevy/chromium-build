# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main.v8.v8_notifier import V8Notifier


def Update(config, active_main, c):
  c['status'].extend([
    V8Notifier(
        config,
        active_main,
        categories_steps={'release': []},
        sendToInterestedUsers=True,
    ),
    V8Notifier(
        config,
        active_main,
        categories_steps={'mips': []},
        extraRecipients=[
          'akos.palfi@imgtec.com',
          'balazs.kilvady@imgtec.com',
          'dusan.milosavljevic@imgtec.com',
          'gergely.kis@imgtec.com',
          'paul.lind@imgtec.com',
        ],
    ),
    V8Notifier(
        config,
        active_main,
        categories_steps={'ppc': []},
        extraRecipients=[
          'mbrandy@us.ibm.com',
          'michael_dawson@ca.ibm.com',
        ],
    ),
    V8Notifier(
        config,
        active_main,
        categories_steps={'s390': []},
        extraRecipients=[
          'joransiu@ca.ibm.com',
          'jyan@ca.ibm.com',
          'michael_dawson@ca.ibm.com',
        ],
    ),
  ])

