# Copyright 2017-2022 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3

from dewi_realtime_sync.filesync_data import FileSyncEntry, FileSyncEntryManager
from dewi_realtime_sync.filesystem import Filesystem, KubernetesFileSystem, LocalFilesystem, RemoteFilesystem
from dewi_realtime_sync.syncers import FileSynchronizer
from dewi_realtime_sync.watchers.watchdog import FileSystemChangeHandler, WatchDog
from dewi_realtime_sync.watchers.watchers import FileSynchronizerWatcher, FileSystemChangeWatcher, \
    SkippableChangeWatcher


class SyncApp:
    def __init__(self, directory: str, target_directory: str,
                 entries: list[FileSyncEntry],
                 filesystem: Filesystem,
                 parallel: int | bool | None = None
                 ):
        self._directory = self._rstrip(directory)
        self._target_directory = self._rstrip(target_directory)
        self._entries = entries
        self._filesystem = filesystem
        self._parallel = parallel

    def _rstrip(self, s: str):
        s = s.rstrip('/')
        return s if s else '/'

    def run(self):
        handler = self._create_watchdog_handler()
        w = WatchDog(self._directory, handler)
        w.run()

    def _create_watchdog_handler(self) -> FileSystemChangeHandler:
        entry_manager = FileSyncEntryManager(self._entries)
        synchronizer = FileSynchronizer(self._directory, self._target_directory, self._filesystem)
        fsw = FileSystemChangeWatcher([self._directory], self._parallel)
        fsw.register_watcher(SkippableChangeWatcher([self._directory]))
        fsw.register_watcher(FileSynchronizerWatcher(synchronizer, entry_manager))
        handler = FileSystemChangeHandler(fsw)
        return handler


class LocalSyncApp(SyncApp):
    def __init__(self, directory: str, target_directory: str,
                 entries: list[FileSyncEntry]):
        super().__init__(directory, target_directory, entries, LocalFilesystem())


class SyncOverSshApp(SyncApp):
    def __init__(self, directory: str, target_directory: str,
                 entries: list[FileSyncEntry],
                 user: str, host: str, port: int,
                 check_host_key: bool = True
                 ):
        super().__init__(directory, target_directory, entries, RemoteFilesystem(user, host, port, check_host_key))


class SyncOverKubernetesApp(SyncApp):
    def __init__(self, directory: str, target_directory: str,
                 entries: list[FileSyncEntry],
                 parallel: int | bool | None,
                 namespace: str, pod: str, container: str
                 ):
        super().__init__(directory, target_directory, entries, KubernetesFileSystem(namespace, pod, container),
                         parallel)
