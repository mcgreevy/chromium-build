# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class WebRTCBranches(Main.Main3a):
  project_name = 'WebRTC Branches'
  main_port = 21301
  subordinate_port = 31301
  main_port_alt = 26301
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-watchlist@google.com'
  tree_closing_notification_recipients = ['webrtc-cb-watchlist@google.com']
  main_domain = 'webrtc.org'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  buildbot_url = 'http://build.chromium.org/p/client.webrtc.branches/'
  service_account_file = 'service-account-webrtc.json'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.webrtc.branches'
