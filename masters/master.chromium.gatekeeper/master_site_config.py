# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class Gatekeeper(Main.Main1):
  project_name = 'Chromium Gatekeeper'
  main_port = 8008
  subordinate_port = 8108
  main_port_alt = 8208
  buildbot_url = 'http://build.chromium.org/p/chromium.gatekeeper/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.gatekeeper'
