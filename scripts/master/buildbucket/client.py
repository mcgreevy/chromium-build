# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file contains buildbucket service client."""

import datetime
import json
import os
import urlparse

from main import auth
from main import deferred_resource
from main.buildbucket import common
import apiclient
import httplib2

BUILDBUCKET_HOSTNAME_PRODUCTION = 'cr-buildbucket.appspot.com'
BUILDBUCKET_HOSTNAME_TESTING = 'cr-buildbucket-test.appspot.com'

THIS_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
DISCOVERY_DOC_PATH = os.path.join(THIS_DIR, 'discovery_doc.json')


def get_default_buildbucket_hostname(main):
  return (
      BUILDBUCKET_HOSTNAME_PRODUCTION if main.is_production_host
      else BUILDBUCKET_HOSTNAME_TESTING)


def create_buildbucket_service(main, hostname=None, verbose=None):
  """Asynchronously creates buildbucket API resource.

  Returns:
    A DeferredResource as Deferred.
  """
  hostname = hostname or get_default_buildbucket_hostname(main)

  cred_factory = deferred_resource.CredentialFactory(
    lambda: auth.create_credentials_for_main(main),
    ttl=datetime.timedelta(minutes=5),
  )

  with open(DISCOVERY_DOC_PATH) as f:
    discovery_doc = json.load(f)

  # This block of code is adapted from
  # https://chromium.googlesource.com/chromium/tools/build/+/08b404f/third_party/google_api_python_client/googleapiclient/discovery.py#146
  # https://chromium.googlesource.com/chromium/tools/build/+/08b404f/third_party/google_api_python_client/googleapiclient/discovery.py#218
  resource = apiclient.discovery.Resource(
      http=httplib2.Http(),
      # Note that this does not include _ah/ in URL path, which means
      # we bypass Cloud Endpoints proxy server. See also:
      # https://bugs.chromium.org/p/chromium/issues/detail?id=626650
      # https://codereview.chromium.org/2117833003/
      # https://codereview.chromium.org/2116783003/
      baseUrl='https://%s/api/buildbucket/v1/' % hostname,
      model=apiclient.model.JsonModel(False),
      requestBuilder=apiclient.http.HttpRequest,
      developerKey=None,
      resourceDesc=discovery_doc,
      rootDesc=discovery_doc,
      schema=apiclient.schema.Schemas(discovery_doc))

  return deferred_resource.DeferredResource(
      resource,
      credentials=cred_factory,
      max_concurrent_requests=10,
      verbose=verbose or False,
      log_prefix=common.LOG_PREFIX,
      timeout=60,
      http_client_name='buildbucket',
  )
