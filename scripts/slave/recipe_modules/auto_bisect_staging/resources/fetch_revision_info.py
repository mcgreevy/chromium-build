#!/usr/bin/python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Gets information about one commit from gitiles.

Example usage:
  ./fetch_revision_info.py 343b531d31 chromium
  ./fetch_revision_info.py 17b4e7450d v8
"""

import argparse
import json
import urllib2

import depot_map  # pylint: disable=relative-import

_GITILES_PADDING = ')]}\'\n'
_URL_TEMPLATE = 'https://chromium.googlesource.com/%s/+/%s?format=json'


def fetch_revision_info(commit_hash, depot_name):
  """Gets information about a chromium revision."""
  path = depot_map.DEPOT_PATH_MAP[depot_name]
  url = _URL_TEMPLATE % (path, commit_hash)
  response = urllib2.urlopen(url).read()
  response_json = response[len(_GITILES_PADDING):]
  response_dict = json.loads(response_json)
  message = response_dict['message'].splitlines()
  subject = message[0]
  body = '\n'.join(message[1:])
  result = {
      'author': response_dict['author']['name'],
      'email': response_dict['author']['email'],
      'subject': subject,
      'body': body,
      'date': response_dict['committer']['time'],
  }
  return result


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('commit_hash')
  parser.add_argument('depot', choices=list(depot_map.DEPOT_PATH_MAP))
  args = parser.parse_args()
  revision_info = fetch_revision_info(args.commit_hash, args.depot)
  print json.dumps(revision_info)


if __name__ == '__main__':
  main()
