# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class V8TryServer(Main.Main4):
  project_name = 'V8 Try Server'
  main_port = 8074
  subordinate_port = 8174
  main_port_alt = 8274
  try_job_port = 8374
  buildbot_url = 'http://build.chromium.org/p/tryserver.v8/'
  from_address = 'v8-dev@googlegroups.com'
  reply_to = 'chrome-troopers+tryserver@google.com'
  base_app_url = 'https://v8-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = None
  code_review_site = 'http://codereview.chromium.org'
  service_account_file = 'service-account-v8.json'
  buildbucket_bucket = 'main.tryserver.v8'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.v8'
