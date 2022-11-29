# Copyright 2017-2022 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3
import multiprocessing

#
# This file contains file watchers for specific systems
#

import os
from concurrent.futures import ThreadPoolExecutor

from dewi_core.logger import log_debug, log_info
from dewi_realtime_sync.filesync_data import FileSyncEntryManager
from dewi_realtime_sync.syncers import FileSynchronizer


class ChangeWatcher:
    """
     A watcher or observer of file changes
     The file change watching behaves as responsibility change: whichever watcher decides that
      it fully processed the file change, it returns True, that it was the watcher's responsibility.

     Argument of each methods:
         path (str): the absolute path of the changed file
     Returns: bool True if the file is processed, and no further watcher is necessary
     """

    def created(self, path: str) -> bool:
        return self.modified(path)

    def modified(self, path: str) -> bool:
        raise NotImplementedError()

    def removed(self, path: str) -> bool:
        raise NotImplementedError()


class SkippableChangeWatcher(ChangeWatcher):
    SUFFIXES = [
        '~',
        '.bak',
        '.egg_info',
        '.pyc',
        '.orig',
        '.rej',
    ]

    PREFIXES = [
        '#',
        '.git',
    ]

    FIRST_PATH_ENTRIES = [
        '.git',
        'build',
        'dist',
    ]

    def __init__(self, root_directories: list[str]):
        self.directories = [(d[:-1] if d.endswith('/') else d) for d in root_directories]

    def modified(self, path: str) -> bool:
        return self._process_change(path)

    def removed(self, path: str) -> bool:
        return self._process_change(path)

    def _process_change(self, changed_file: str) -> bool:
        if self._skip_based_on_basename(os.path.basename(changed_file)):
            log_debug(f'{self.__class__.__name__}: skip file by basename', filename=changed_file)
            return True

        for directory in self.directories:
            if not changed_file.startswith(directory):
                continue

            path = changed_file[len(directory) + 1:]

            if self._skip_based_on_path(path):
                log_debug(f'{self.__class__.__name__}: skip file by path', filename=changed_file)
                return True

        return False

    def _skip_based_on_basename(self, basename: str) -> bool:
        if basename[0] == '.':
            if basename[-4:-1] == '.sw':
                return True
        else:
            for suffix in self.SUFFIXES:
                if basename.endswith(suffix):
                    return True

            for prefix in self.PREFIXES:
                if basename.startswith(prefix):
                    return True

            if basename == '.DS_Store':
                return True

        return False

    def _skip_based_on_path(self, path: str) -> bool:
        parts = os.path.split(path)
        if parts[0] in self.FIRST_PATH_ENTRIES:
            return True

        if '__pycache__' in parts:
            return True

        return False


class FileSynchronizerWatcher(ChangeWatcher):
    def __init__(self, fs: FileSynchronizer, fm: FileSyncEntryManager):
        self._synchronizer = fs
        self._manager = fm

    def modified(self, path: str) -> bool:
        return self._process_change(path)

    def removed(self, path: str) -> bool:
        return self._process_change(path)

    def _process_change(self, changed_file: str):
        if not changed_file.startswith(self._synchronizer.local_root_directory):
            return False

        local_path = changed_file[len(self._synchronizer.local_root_directory) + 1:]

        detailed_entry = self._manager.get_entry(local_path)
        if detailed_entry is None:
            return False

        self._synchronizer.sync(changed_file, detailed_entry)

        return True


class FileSystemChangeWatcher:
    _executor: ThreadPoolExecutor | None

    def __init__(self, directories: list[str], parallel: int | bool | None):
        self._directories = list(directories)
        self._watchers = list()
        self._thread_count = 1
        self._executor = None

        self._prepare_threading(parallel)

    def _prepare_threading(self, parallel):
        if isinstance(parallel, int):
            self._thread_count = parallel if parallel > 1 or parallel == 0 else 1
        elif isinstance(parallel, bool):
            self._thread_count = 1 if not parallel else 0

        if self._thread_count == 1:
            return
        elif self._thread_count == 0:
            self._thread_count = max(1, multiprocessing.cpu_count() - 1)

        self._executor = ThreadPoolExecutor(self._thread_count)

    def register_watcher(self, watcher: ChangeWatcher):
        log_debug('Registering change watcher', {'class': type(watcher).__name__})
        self._watchers.append(watcher)

    def created(self, path: str):
        self._process_change(path, 'created', 'created')

    def modified(self, path: str):
        self._process_change(path, 'modified', 'modified')

    def removed(self, path: str):
        self._process_change(path, 'deleted', 'removed')

    def _process_change(self, path: str, change_type: str, callback: str):
        log_info('Process change', change_type=change_type, method=callback, path=path, threaded=self._thread_count > 1)
        if self._executor:
            self._executor.submit(self._process_change_cb, path, change_type, callback, True)
        else:
            self._process_change_cb(path, change_type, callback, False)

    def _process_change_cb(self, path: str, change_type: str, callback: str, log: bool):
        if log:
            log_info('Process change, call watchers', change_type=change_type, method=callback, path=path)

        for watcher in self._watchers:
            processed = getattr(watcher, callback)(path)

            if processed:
                return
