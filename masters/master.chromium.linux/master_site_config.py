# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class ChromiumLinux(Main.Main1):
  project_name = 'Chromium Linux'
  main_port = 8087
  subordinate_port = 8187
  main_port_alt = 8287
  buildbot_url = 'http://build.chromium.org/p/chromium.linux/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.linux'
