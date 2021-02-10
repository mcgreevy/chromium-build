# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class BlinkTryServer(Main.Main4):
  project_name = 'Blink Try Server'
  main_port = 8009
  subordinate_port = 8109
  main_port_alt = 8209
  buildbot_url = 'http://build.chromium.org/p/tryserver.blink/'
  # Select tree status urls and codereview location.
  reply_to = 'chrome-troopers+tryserver@google.com'
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  last_good_blink_url = 'http://blink-status.appspot.com/lkgr'
  service_account_file = 'service-account-chromium-tryserver.json'
  buildbucket_bucket = 'main.tryserver.blink'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.blink'
