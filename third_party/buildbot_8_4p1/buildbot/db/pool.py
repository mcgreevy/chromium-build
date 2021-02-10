# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import time
import os
import sqlalchemy as sa
import twisted
from buildbot.process import metrics
from twisted.internet import reactor, threads, defer
from twisted.python import threadpool, failure, versions, log


class DBThreadPool(threadpool.ThreadPool):

    running = False

    # Some versions of SQLite incorrectly cache metadata about which tables are
    # and are not present on a per-connection basis.  This cache can be flushed
    # by querying the sqlite_main table.  We currently assume all versions of
    # SQLite have this bug, although it has only been observed in 3.4.2.  A
    # dynamic check for this bug would be more appropriate.  This is documented
    # in bug #1810.
    __broken_sqlite = False

    def __init__(self, engine):
        pool_size = 5

        # If the engine has an C{optimal_thread_pool_size} attribute, then the
        # maxthreads of the thread pool will be set to that value.  This is
        # most useful for SQLite in-memory connections, where exactly one
        # connection (and thus thread) should be used.
        if hasattr(engine, 'optimal_thread_pool_size'):
            pool_size = engine.optimal_thread_pool_size

        threadpool.ThreadPool.__init__(self,
                        minthreads=1,
                        maxthreads=pool_size,
                        name='DBThreadPool')
        self.engine = engine
        if engine.dialect.name == 'sqlite':
            vers = self.get_sqlite_version()
            log.msg("Using SQLite Version %s" % (vers,))
            if vers < (3,7):
                log.msg("NOTE: this old version of SQLite does not support "
                        "WAL journal mode; a busy main may encounter "
                        "'Database is locked' errors.  Consider upgrading.")
            if vers < (3,4):
                log.msg("NOTE: this old version of SQLite is not supported. "
                        "It fails for multiple simultaneous accesses to the "
                        "database: try adding the 'pool_size=1' argument to "
                        "your db url. ")
            brkn = self.__broken_sqlite = self.detect_bug1810()
            if brkn:
                log.msg("Applying SQLite workaround from Buildbot bug #1810")
        self._start_evt = reactor.callWhenRunning(self._start)

    def _start(self):
        self._start_evt = None
        if not self.running:
            self.start()
            self._stop_evt = reactor.addSystemEventTrigger(
                    'during', 'shutdown', self._stop)
            self.running = True

    def _stop(self):
        self._stop_evt = None
        self.stop()
        self.engine.dispose()
        self.running = False

    def shutdown(self):
        """Manually stop the pool.  This is only necessary from tests, as the
        pool will stop itself when the reactor stops under normal
        circumstances."""
        if not self._stop_evt:
            return # pool is already stopped
        reactor.removeSystemEventTrigger(self._stop_evt)
        self._stop()

    # Try about 170 times over the space of a day, with the last few tries
    # being about an hour apart.  This is designed to span a reasonable amount
    # of time for repairing a broken database server, while still failing
    # actual problematic queries eventually
    BACKOFF_START = 1.0
    BACKOFF_MULT = 1.05
    MAX_OPERATIONALERROR_TIME = 3600*24 # one day
    def __thd(self, with_engine, callable, args, kwargs):
        # try to call callable(arg, *args, **kwargs) repeatedly until no
        # OperationalErrors occur, where arg is either the engine (with_engine)
        # or a connection (not with_engine)
        backoff = self.BACKOFF_START
        start = time.time()
        while True:
            if with_engine:
                arg = self.engine
            else:
                arg = self.engine.contextual_connect()

            if self.__broken_sqlite: # see bug #1810
                arg.execute("select * from sqlite_main")
            try:
                rv = callable(arg, *args, **kwargs)
                assert not isinstance(rv, sa.engine.ResultProxy), \
                        "do not return ResultProxy objects!"
            except sa.exc.OperationalError, e:
                text = e.orig.args[0]
                if "Lost connection" in text \
                    or "database is locked" in text:

                    # see if we've retried too much
                    elapsed = time.time() - start
                    if elapsed > self.MAX_OPERATIONALERROR_TIME:
                        raise

                    metrics.MetricCountEvent.log(
                            "DBThreadPool.retry-on-OperationalError")
                    log.msg("automatically retrying query after "
                            "OperationalError (%ss sleep)" % backoff)

                    # sleep (remember, we're in a thread..)
                    time.sleep(backoff)
                    backoff *= self.BACKOFF_MULT

                    # and re-try
                    continue
                else:
                    raise
            finally:
                if not with_engine:
                    arg.close()
            break
        return rv

    def do(self, callable, *args, **kwargs):
        return threads.deferToThreadPool(reactor, self,
                self.__thd, False, callable, args, kwargs)

    def do_with_engine(self, callable, *args, **kwargs):
        return threads.deferToThreadPool(reactor, self,
                self.__thd, True, callable, args, kwargs)

    # older implementations for twisted < 0.8.2, which does not have
    # deferToThreadPool; this basically re-implements it, although it gets some
    # of the synchronization wrong - the thread may still be "in use" when the
    # deferred fires in the parent, which can lead to database accesses hopping
    # between threads.  In practice, this should not cause any difficulty.
    if twisted.version < versions.Version('twisted', 8, 2, 0):
        def __081_wrap(self, with_engine, callable, args, kwargs): # pragma: no cover
            d = defer.Deferred()
            def thd():
                try:
                    reactor.callFromThread(d.callback,
                            self.__thd(with_engine, callable, args, kwargs))
                except:
                    reactor.callFromThread(d.errback,
                            failure.Failure())
            self.callInThread(thd)
            return d

        def do_081(self, callable, *args, **kwargs): # pragma: no cover
            return self.__081_wrap(False, callable, args, kwargs)

        def do_with_engine_081(self, callable, *args, **kwargs): # pragma: no cover
            return self.__081_wrap(True, callable, args, kwargs)

        do = do_081
        do_with_engine = do_with_engine_081

    def detect_bug1810(self):
        # detect buggy SQLite implementations; call only for a known-sqlite
        # dialect
        try:
            import pysqlite2.dbapi2 as sqlite
            sqlite = sqlite
        except ImportError:
            import sqlite3 as sqlite

        dbfile = "detect_bug1810.db"
        def test(select_from_sqlite_main=False):
            try:
                conn1 = sqlite.connect(dbfile)
                curs1 = conn1.cursor()
                curs1.execute("PRAGMA table_info('foo')")

                conn2 = sqlite.connect(dbfile)
                curs2 = conn2.cursor()
                curs2.execute("CREATE TABLE foo ( a integer )")

                if select_from_sqlite_main:
                    curs1.execute("SELECT * from sqlite_main")
                curs1.execute("SELECT * from foo")
            finally:
                conn1.close()
                conn2.close()
                os.unlink(dbfile)

        try:
            test()
        except sqlite.OperationalError:
            # this is the expected error indicating it's broken
            return True

        # but this version should not fail..
        test(select_from_sqlite_main=True)
        return False # not broken - no workaround required

    def get_sqlite_version(self):
        engine = sa.create_engine('sqlite://')
        conn = engine.contextual_connect()

        try:
            r = conn.execute("SELECT sqlite_version()")
            vers_row = r.fetchone()
            r.close()
        except:
            return (0,)

        if vers_row:
            try:
                return tuple(map(int, vers_row[0].split('.')))
            except (TypeError, ValueError):
                return (0,)
        else:
            return (0,)
