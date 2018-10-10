from dataclasses import dataclass

import re
import socket
import threading
import tailer
import time


@dataclass
class File:
    path: str
    regexp: object

    def __hash__(self):
        return id(self)


class CollectorThread(threading.Thread):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.graceful_shutdown = threading.Event()


class AlreadyStarted(Exception):
    pass


class NotStarted(Exception):
    pass


class Registry(object):
    def __init__(self):
        self.logfiles = []

    def register(self, path, regexp):
        self.logfiles.append(File(path, re.compile(regexp)))

    def get_all(self):
        return self.logfiles[:]


class ScreenOutput(object):
    def write(self, identifier, path, data):
        print(identifier, path, data)


class FileOutput(object):
    def __init__(self, output_path):
        self.output = open(output_path, 'w')

    def write(self, identifier, path, data):
        self.output.write('[%s] %s' % (identifier, data))
        self.output.flush()


class Collector(object):
    def __init__(self, registry, output, identifier=None):
        self.logs = registry
        self.identifier = identifier or socket.gethostname()
        self.output = output
        self.canceller = threading.Event()
        self._started = False
        self._threads = {}

    def log_stream(self, log):
        for line in tailer.follow(open(log.path)):
            data = log.regexp.match(line).groupdict()
            self.output.write(self.identifier, log.path, data)
            if self.canceller.is_set():
                return

    def start(self):
        if self._started:
            raise AlreadyStarted

        self.canceller.clear()
        self._threads.clear()

        for log in self.logs.get_all():
            self._create_thread(log).start()

        self._started = True

    def _create_thread(self, log):
        t = CollectorThread(
                target=self.log_stream, args=(log,), daemon=True)
        self._threads[log] = t
        return t

    def join(self):
        if not self._started:
            raise NotStarted

        while True:
            time.sleep(1)

    def stop(self):
        if self._started:
            self.canceller.set()
            for t in self._threads.values():
                t.join()
            self._started = False
        else:
            raise NotStarted

    def notify_update(self):
        all_logs = self.logs.get_all()

        for log in all_logs:
            if log not in self._threads:
                self._create_thread(log).start()

        for log in self._threads.keys():
            if log not in all_logs:
                t = self._threads.pop(log)
                t.graceful_shutdown.set()


default_registry = Registry()
default_collector = Collector(default_registry, ScreenOutput())

# shortcut funcs


def register(path, regexp):
    default_registry.register(path, regexp)
    default_collector.notify_update()


def start():
    default_collector.start()


def stop():
    default_collector.stop()


def wait():
    default_collector.join()


def set_output(output):
    default_collector.output = output


def set_identifier(identifier):
    default_collector.identifier = identifier
