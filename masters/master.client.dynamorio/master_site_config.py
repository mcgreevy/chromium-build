# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class DynamoRIO(Main.Main3):
  project_name = 'DynamoRIO'
  main_port = 8059
  subordinate_port = 8159
  main_port_alt = 8259
  buildbot_url = 'http://build.chromium.org/p/client.dynamorio/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.dynamorio'
