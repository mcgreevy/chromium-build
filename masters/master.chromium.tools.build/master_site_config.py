# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/main_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMain definition."""

from config_bootstrap import Main

class ChromiumToolsBuild(Main.Main1):
  project_name = 'ChromiumToolsBuild'
  main_port = 20103
  subordinate_port = 30103
  main_port_alt = 25103
  buildbot_url = 'https://build.chromium.org/p/chromium.tools.build/'
  buildbucket_bucket = None
  service_account_file = None
  # To enable outbound pubsub event streaming.
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.tools.build'
