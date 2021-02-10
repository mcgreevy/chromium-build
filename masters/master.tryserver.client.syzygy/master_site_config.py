# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/main_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMain definition."""

from config_bootstrap import Main

class SyzygyTryserver(Main.Main4a):
  project_name = 'SyzygyTryserver'
  main_port = 21404
  subordinate_port = 31404
  main_port_alt = 26404
  buildbot_url = 'https://build.chromium.org/p/tryserver.client.syzygy/'
  buildbucket_bucket = 'main.tryserver.client.syzygy'
  service_account_file = 'service-account-chromium-tryserver.json'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.client.syzygy'
