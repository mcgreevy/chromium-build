# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class DartFYI(Main.Main3):
  project_name = 'Dart FYI'
  main_port = 8055
  subordinate_port = 8155
  # Enable when there's a public waterfall.
  main_port_alt = 8255
  buildbot_url = 'http://build.chromium.org/p/client.dart.fyi/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.dart.fyi'
