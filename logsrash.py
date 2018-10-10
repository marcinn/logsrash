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
    parser: object

    def __hash__(self):
        return id(self)


class CollectorThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        kwargs['target'] = self._collect_log
        super().__init__(*args, **kwargs)
        self.graceful_shutdown = threading.Event()

    def _collect_log(self, identifier, log, output, canceller):
        for line in tailer.follow(open(log.path)):
            try:
                data = log.regexp.match(line).groupdict()
            except AttributeError:
                data = {}
            else:
                data = log.parser.parse(data)

            output.write(identifier, log.path, data)

            if self.graceful_shutdown.is_set() or canceller.is_set():
                return


class AlreadyStarted(Exception):
    pass


class NotStarted(Exception):
    pass


class NoopParser(object):
    def parse(self, data):
        return data


noop_parser = NoopParser()


class Registry(object):
    def __init__(self):
        self.logfiles = []

    def register(self, path, regexp, parser=noop_parser):
        self.logfiles.append(File(path, re.compile(regexp), parser))

    def get_all(self):
        return self.logfiles[:]

    def clear_all(self):
        self.logfiles = []


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
            daemon=True, kwargs={
                'identifier': self.identifier, 'log': log,
                'canceller': self.canceller, 'output': self.output})
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
        if not self._started:
            return

        all_logs = self.logs.get_all()

        for log in all_logs:
            if log not in self._threads:
                self._create_thread(log).start()

        for log in list(self._threads.keys()):
            if log not in all_logs:
                t = self._threads.pop(log)
                t.graceful_shutdown.set()


default_registry = Registry()
default_collector = Collector(default_registry, ScreenOutput())

# shortcut funcs


def register(path, regexp, parser=noop_parser):
    default_registry.register(path, regexp, parser)
    default_collector.notify_update()


def unregister_all():
    default_registry.clear_all()
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
