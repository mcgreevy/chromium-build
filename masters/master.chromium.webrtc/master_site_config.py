# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class ChromiumWebRTC(Main.Main1):
  project_name = 'Chromium WebRTC'
  main_port = 8054
  subordinate_port = 8154
  main_port_alt = 8254
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'chromium-webrtc-cb-watchlist@google.com'
  base_app_url = 'https://webrtc-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  buildbot_url = 'http://build.chromium.org/p/chromium.webrtc/'
  service_account_file = 'service-account-webrtc.json'
  buildbucket_bucket = 'main.chromium.webrtc'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.webrtc'
