# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
from datetime import datetime

from twisted.python import log
from twisted.internet import reactor


class FloatingSet(object):
  """A set describing available primary/floating subordinates."""
  def __init__(self):
    self._primary = set()
    self._floating = set()

  def AddPrimary(self, *s):
    self._primary.update(s)

  def AddFloating(self, *s):
    self._floating.update(s)

  def NextSubordinateFunc(self, grace_period):
    """Returns a NextSubordinateFunc that uses the contents of this set."""
    return _FloatingNextSubordinateFunc(self, grace_period)

  def Get(self):
    return (sorted(self._primary), sorted(self._floating))

  def __str__(self):
    return '%s > %s' % (
        ', '.join(sorted(self._primary)),
        ', '.join(sorted(self._floating)))


class PokeBuilderTimer(object):
  def __init__(self, botmain, buildername):
    self.botmain = botmain
    self.buildername = buildername
    self.delayed_call = None

  def cancel(self):
    if self.delayed_call is not None:
      self.delayed_call.cancel()
      self.delayed_call = None

  def reset(self, delta):
    if self.delayed_call is not None:
      current_delta = (datetime.fromtimestamp(self.delayed_call.getTime()) -
                       _get_now())
      if delta < current_delta:
        self.delayed_call.reset(delta.total_seconds())
      return

    # Schedule a new call
    self.delayed_call = reactor.callLater(
        delta.total_seconds(),
        self._poke,
    )

  def _poke(self):
    self.delayed_call = None
    log.msg('Poking builds for builder [%s]' % (self.buildername,))
    self.botmain.maybeStartBuildsForBuilder(self.buildername)


class _FloatingNextSubordinateFunc(object):
  """
  This object, when used as a Builder's 'nextSubordinate' function, allows a strata-
  based preferential treatment to be assigned to a Builder's Subordinates.

  The 'nextSubordinate' function is called on a scheduled build when an associated
  subordinate becomes available, either coming online or finishing an existing build.
  These events are used as stimulus to enable the primary builder(s) to pick
  up builds when appropriate.

  1) If a Primary is available, the build will be assigned to them.
  2) If a Primary builder is busy or is still within its grace period for
    unavailability, no subordinate will be assigned in anticipation of the
    'nextSubordinate' being re-invoked once the builder returns (1). If the grace
    period expires, we "poke" the main to call 'nextSubordinate', at which point
    the build will fall through to a lower strata.
  3) If a Primary subordinate is offline past its grace period, the build will be
    assigned to a Floating subordinate.

  Args:
    fs (FloatingSet): The set of available primary/floating subordinates.
    grace_period: (timedelta) The amount of time that a subordinate can be offline
        before builds fall through to a lower strata.
  """

  def __init__(self, fs, grace_period):
    self._primary, self._floating = fs.Get()
    self._fs = fs
    self._grace_period = grace_period
    self._poke_builder_timers = {}
    self.verbose = False

    started = _get_now()
    self._subordinate_seen_times = dict((s, started) for s in itertools.chain(
        self._primary, self._floating))

  def __repr__(self):
    return '%s(%s)' % (type(self).__name__, self._fs)

  def __call__(self, builder, subordinate_builders):
    """Main 'nextSubordinate' invocation point.

    When this is called, we are given the following information:
    - The Builder
    - A set of 'SubordinateBuilder' instances that are available and ready for
      assignment (subordinate_builders).
    - The total set of ONLINE 'SubordinateBuilder' instances associated with
      'builder' (builder.subordinates)
    - The set of all subordinates configured for Builder (via
      '_get_all_subordinate_status')

    We compile that into a stateful awareness and use it as a decision point.
    Based on the subordinate availability and grace period, we will either:
    (1) Return a subordinate immediately to claim this build. We do this if:
      (1a) There was a "primary" build subordinate available, or
      (1b) We are outside of all of the grace periods for the primary subordinates,
           and there is a floating builder available.
    (2) Return 'None' (delaying the build) in anticipation of primary/floating
        availability.

    If we go with (2), we will schedule a 'poke' timer to stimulate a future
    'nextSubordinate' call, since BuildBot only checks for builds on explicit subordinate
    availability edges. This covers the case where floating builders are
    available, but aren't enlisted because we're within the grace period. In
    this case, we need to re-evaluate subordinates after the grace period expires,
    but actual subordinate state won't haev changed, so no new subordinate availabilty edge
    will have occurred.
    """
    self._debug("Calling [%s] with builder=[%s], subordinates=[%s]",
                self, builder, subordinate_builders)
    self._cancel_builder_timer(builder)

    # Get the set of all 'SubordinateStatus' assigned to this Builder (idle, busy,
    # and offline).
    subordinate_status_map = dict(
        (subordinate_status.name, subordinate_status)
        for subordinate_status in self._get_all_subordinate_status(builder)
    )

    # Record the names of the subordinates that were proposed.
    proposed_subordinate_builder_map = {}
    for subordinate_builder in subordinate_builders:
      proposed_subordinate_builder_map[subordinate_builder.subordinate.subordinatename] = subordinate_builder

    # Calculate the oldest a subordinate can be before we assume something's wrong.
    now = _get_now()
    grace_threshold = (now - self._grace_period)

    # Record the last time we've seen any of these subordinates online.
    online_subordinate_builders = set()
    for subordinate_builder in builder.subordinates:
      build_subordinate = subordinate_builder.subordinate
      if build_subordinate is None:
        continue
      self._record_subordinate_seen_time(build_subordinate, now)
      online_subordinate_builders.add(build_subordinate.subordinatename)

    self._debug('Online proposed subordinates: [%s]',
                subordinate_builders)

    # Are there any primary subordinates that are proposed? If so, use it
    within_grace_period = []
    some_primary_were_busy = False
    wait_delta = None
    for subordinate_name in self._primary:
      self._debug('Considering primary subordinate [%s]', subordinate_name)

      # Was this subordinate proposed to 'nextSubordinate'?
      subordinate_builder = proposed_subordinate_builder_map.get(subordinate_name)
      if subordinate_builder is not None:
        # Yes. Use it!
        self._debug('Subordinate [%s] is available', subordinate_name)
        return subordinate_builder

      # Is this subordinate online? If so, we won't consider floating candiates.
      if subordinate_name in online_subordinate_builders:
        # The subordinate is online, but is not proposed (BUSY); add it to the
        # desired subordinates list.
        self._debug('Subordinate [%s] is online but BUSY.', subordinate_name)
        within_grace_period.append(subordinate_name)
        some_primary_were_busy = True
        continue

      # The subordinate is offline. Is this subordinate within the grace period?
      subordinate_status = subordinate_status_map.get(subordinate_name)
      last_seen = self._get_latest_seen_time(subordinate_name, subordinate_status)
      if last_seen < grace_threshold:
        # No, the subordinate is older than our grace period.
        self._debug('Subordinate [%s] is OFFLINE and outside grace period '
                    '(%s < %s).', subordinate_name, last_seen, grace_threshold)
        continue

      # This subordinate is within its grace threshold. Add it to the list of
      # desired subordinates from this set and update our wait delta in case we
      # have to poke.
      #
      # We track the longest grace period delta, since after this point if
      # no subordinates have taken the build we would otherwise hang.
      self._debug('Subordinate %r is OFFLINE but within grace period '
                  '(%s >= %s).', subordinate_name, last_seen, grace_threshold)
      within_grace_period.append(subordinate_name)
      subordinate_wait_delta = (self._grace_period - (now - last_seen))
      if (wait_delta is None) or (subordinate_wait_delta > wait_delta):
        wait_delta = subordinate_wait_delta

    # We've looped through all primary subordinates, and none of them were available.
    # Were some within the grace period?
    if not within_grace_period:
      # We're outside of our grace period. Are there floating subordinates that we
      # can use?
      for subordinate_name in self._floating:
        subordinate_builder = proposed_subordinate_builder_map.get(subordinate_name)
        if subordinate_builder is not None:
          # Yes. Use it!
          self._debug('Subordinate [%s] is available', subordinate_name)
          return subordinate_builder

      self._debug('No subordinates are available; returning None')
      return None

    # We're going to return 'None' to wait for a primary subordinate. If all of
    # the subordinates that we're anticipating are offline, schedule a 'poke'
    # after the last candidate has exceeded its grace period to allow the
    # build to go to lower strata.
    log.msg('Returning None in anticipation of unavailable primary subordinates. '
            'Please disregard the following BuildBot `nextSubordinate` '
            'error: %s' % (within_grace_period,))

    if (not some_primary_were_busy) and (wait_delta is not None):
      self._debug('Scheduling ping for [%s] in [%s]',
                  builder.name, wait_delta)
      self._schedule_builder_timer(builder, wait_delta)
    return None

  def _debug(self, fmt, *args):
    if not self.verbose:
      return
    log.msg(fmt % args)

  @staticmethod
  def _get_all_subordinate_status(builder):
    # Try using the builder's BuilderStatus object to get a list of all subordinates
    if builder.builder_status is not None:
      return builder.builder_status.getSubordinates()

    # Satisfy with the list of currently-connected subordinates
    return [subordinate_builder.subordinate.subordinate_status
            for subordinate_builder in builder.subordinates]

  def _get_latest_seen_time(self, subordinate_name, subordinate_status):
    times = [self._subordinate_seen_times[subordinate_name]]

    if subordinate_status:
      # Add all of the registered connect times
      times += [datetime.fromtimestamp(connect_time)
                for connect_time in subordinate_status.connect_times]

      # Add the time of the subordinate's last message
      times.append(datetime.fromtimestamp(subordinate_status.lastMessageReceived()))

    return max(times)

  def _record_subordinate_seen_time(self, build_subordinate, now):
    self._subordinate_seen_times[build_subordinate.subordinatename] = now

  def _schedule_builder_timer(self, builder, delta):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      poke_builder_timer = PokeBuilderTimer(
          builder.botmain,
          builder.name,
      )
      self._poke_builder_timers[builder.name] = poke_builder_timer
    poke_builder_timer.reset(delta)

  def _cancel_builder_timer(self, builder):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      return
    poke_builder_timer.cancel()


def _get_now():
  """Returns (datetime.datetime): The current time.

  This exists so it can be overridden by mocks in unit tests.
  """
  return datetime.now()
