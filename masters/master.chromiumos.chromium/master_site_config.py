# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class ChromiumOSChromium(Main.Main2a):
  project_name = 'ChromiumOS Chromium'
  main_port_id = 3
  buildbot_url = 'http://build.chromium.org/p/chromiumos.chromium/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromiumos.chromium'
