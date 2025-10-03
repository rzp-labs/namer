"""
A file watching service to rename movie files and move them
to relevant locations after match the file against the theporndb.
"""

import os
import shutil
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from platform import system
from queue import Queue
from threading import Thread
from typing import Optional

import schedule
from loguru import logger
from watchdog.events import EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED, FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserver

from namer.command import Command, gather_target_files_from_dir, is_interesting_movie, make_command_relative_to, move_command_files
from namer.configuration import NamerConfig
from namer.configuration_utils import verify_configuration
from namer.metadataapi import get_user_info
from namer.name_formatter import PartialFormatter
from namer.namer import process_file
from namer.web.server import NamerWebServer
from namer.logging_utils import setup_file_logging


def __is_file_in_use_windows(file: Path):
    try:
        file.rename(file)
    except PermissionError:
        return True
    else:
        return False


def __is_file_in_use_unix(file: Path):
    try:
        # pylint: disable=consider-using-with
        buffered_reader = open(file, mode='rb')  # noqa: SIM115
        buffered_reader.close()
    except PermissionError:
        return True
    else:
        return False


def is_file_in_use(file: Optional[Path]):
    if not file or not file.exists():
        return False

    if system() == 'Windows':
        return __is_file_in_use_windows(file)
    else:
        return __is_file_in_use_unix(file)


def done_copying(file: Optional[Path]) -> bool:
    """
    Determines if a file is being copied by checking its size in 2 second
    increments and seeing if the size has stayed the same.
    """
    if not file or not file.exists():
        return False

    while is_file_in_use(file):
        time.sleep(2)

    return True


@logger.catch
def handle(command: Command):
    """
    Responsible for processing and moving new movie files.
    """
    process_file(command)


def _require_config_path(config: NamerConfig, attr: str) -> Path:
    value = getattr(config, attr, None)
    if not value:
        raise ValueError(f'NamerConfig is missing required "{attr}" configuration path')
    if not isinstance(value, Path):
        raise TypeError(f'NamerConfig "{attr}" configuration path must be a pathlib.Path, got {type(value).__name__}')
    return value


def _path_is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(base.resolve(strict=False))
    except ValueError:
        return False
    return True


def retry_failed(namer_config: NamerConfig):
    """
    Moves the contents from the failed dir to the watch dir to attempt reprocessing.
    """
    try:
        failed_dir = _require_config_path(namer_config, 'failed_dir')
        watch_dir = _require_config_path(namer_config, 'watch_dir')
    except (AttributeError, ValueError, TypeError) as error:
        logger.error(error)
        return

    logger.info('Retry failed items:')

    # remove all old namer log files
    for log_file in failed_dir.rglob('**/*_namer.json.gz'):
        log_file.unlink()

    # move all files back to watch dir.
    for file in gather_target_files_from_dir(failed_dir, namer_config):
        target = file.target_directory.name if file.parsed_dir_name and file.target_directory else file.target_movie_file.name
        shutil.move(failed_dir / target, watch_dir / target)


def is_fs_case_sensitive():
    """
    Create a temporary file to determine if a filesystem is case-sensitive, or not.
    """
    with tempfile.NamedTemporaryFile(prefix='TmP') as tmp_file:
        return not Path(tmp_file.name.lower()).is_file()


class MovieEventHandler(PatternMatchingEventHandler):
    """
    When a new movie file is detected, this class handles the event,
    and passes off the processing to the handler() function above.
    """

    __namer_config: NamerConfig
    __command_queue: Queue
    __watch_dir: Path
    __work_dir: Path

    def __init__(self, namer_config: NamerConfig, enqueue_work_fn, command_queue: Queue):
        super().__init__(patterns=['*.*'], case_sensitive=is_fs_case_sensitive(), ignore_directories=True, ignore_patterns=None)
        self.__namer_config = namer_config
        self.__enqueue_work_fn = enqueue_work_fn
        self.__command_queue = command_queue
        self.__watch_dir = _require_config_path(namer_config, 'watch_dir')
        self.__work_dir = _require_config_path(namer_config, 'work_dir')

    def on_any_event(self, event: FileSystemEvent):
        file_path = None
        if event.event_type == EVENT_TYPE_MOVED:
            file_path = event.dest_path  # type: ignore
        elif event.event_type != EVENT_TYPE_MODIFIED:
            file_path = event.src_path

        if file_path:
            if isinstance(file_path, bytes):
                try:
                    file_path = file_path.decode('utf-8', errors='replace')
                except Exception as error:  # pragma: no cover - defensive logging
                    logger.error('Failed to decode file path: %s', error)
                    return
            if not isinstance(file_path, str):
                logger.error('unexpected file path type %s', type(file_path))
                return

            path = Path(file_path).resolve()
            if not _path_is_within(self.__watch_dir, path):
                logger.error('file should be in watch dir {}', path)
                return

            relative_path = str(path.relative_to(self.__watch_dir))
            if not self.__namer_config.ignored_dir_regex.search(relative_path) and is_interesting_movie(path, self.__namer_config) and done_copying(path):
                logger.info('watchdog process called for {}', relative_path)

                # Extra wait time in case other files are copies in as well.
                if self.__namer_config.del_other_files:
                    time.sleep(self.__namer_config.extra_sleep_time)

                if self.__namer_config.queue_limit > 0:
                    while self.__command_queue.qsize() >= self.__namer_config.queue_limit:
                        time.sleep(self.__namer_config.queue_sleep_time)

                self.prepare_file_for_processing(path)

    @logger.catch
    def prepare_file_for_processing(self, path: Path):
        command = make_command_relative_to(input_dir=path, relative_to=self.__watch_dir, config=self.__namer_config)
        working_command = move_command_files(command, self.__work_dir)
        if working_command is not None:
            self.__enqueue_work_fn(working_command)


class MovieWatcher:
    """
    Watches a configured dir for new files and attempts
    to process them and move to a destination dir.

    If a failure occurs moves the new files to a failed dir.

    See NamerConfig
    """

    def enqueue_work(self, command: Command):
        queue_items = list(self.__command_queue.queue)
        items = list(map(lambda x: x.get_command_target(), filter(lambda i: i is not None, queue_items)))
        if not self.__stopped and command.get_command_target() not in items or command is None:
            self.__command_queue.put(command)
        else:
            raise RuntimeError('Command not added to work queue, server is stopping')

    def __processing_thread(self):
        while True:
            command = self.__command_queue.get()
            if command is None:
                logger.info('Marking None task as done')
                self.__command_queue.task_done()
                break

            handle(command)
            self.__command_queue.task_done()

        # Throw away any items after the None item is processed.
        with self.__command_queue.mutex:
            self.__command_queue.queue.clear()

        logger.info('exit processing_thread')

    def __init__(self, namer_config: NamerConfig):
        self.__started = False
        self.__stopped = False
        self.__namer_config = namer_config
        self.__src_path = _require_config_path(namer_config, 'watch_dir')
        self.__event_observer = PollingObserver()
        self.__webserver: Optional[NamerWebServer] = None
        self.__command_queue: Queue = Queue(maxsize=self.__namer_config.queue_limit)
        self.__worker_thread: Thread = Thread(target=self.__processing_thread, daemon=True)
        self.__event_handler = MovieEventHandler(namer_config, self.enqueue_work, self.__command_queue)
        self.__background_thread: Optional[Thread] = None

    def get_config(self) -> NamerConfig:
        return self.__namer_config

    def run(self):
        """
        Checks for new files in 3 second intervals,
        needed if running in docker as events aren't properly passed in.
        """
        if not self.__started:
            self.start()
            if self.__namer_config.web:
                self.__webserver = NamerWebServer(self.__namer_config, self.__command_queue)
                self.__webserver.start()

            try:
                while not self.__stopped:
                    schedule.run_pending()
                    time.sleep(3)
                self.stop()
            except KeyboardInterrupt:
                self.stop()

            self.__started = False
            self.__stopped = False

    def __enter__(self):
        self.__background_thread = Thread(target=self.run)
        self.__background_thread.start()

        if self.__namer_config.web:
            tries = 0
            while not self.get_web_port() and tries < 20:
                time.sleep(0.2)
                tries += 1

            if not self.get_web_port():
                raise RuntimeError('application did not get assigned a port within 4 seconds.')

        return self

    def __simple_exit__(self):
        self.stop()
        if self.__background_thread:
            logger.info('Background thread join')
            self.__background_thread.join()
            logger.info('Background thread joined')
            self.__background_thread = None

    def __exit__(self, exc_type, exc_value, traceback):
        self.__simple_exit__()

    def start(self):
        """
        starts a background thread to check for files.
        """
        config = self.__namer_config
        provider_name = config.metadata_provider.upper()
        watch_dir = _require_config_path(config, 'watch_dir')
        logger.info('Start {} metadata watcher.... watching: {}', provider_name, watch_dir)

        if os.environ.get('PROJECT_VERSION'):
            project_version = os.environ.get('PROJECT_VERSION')
            print(f'Namer version: {project_version}')

        if os.environ.get('BUILD_DATE'):
            build_date = os.environ.get('BUILD_DATE')
            print(f'Built on: {build_date}')

        if os.environ.get('GIT_HASH'):
            git_hash = os.environ.get('GIT_HASH')
            print(f'Git Hash: {git_hash}')

        self.__schedule()
        self.__event_observer.start()
        self.__worker_thread.start()

        # touch all existing movie files.
        with suppress(FileNotFoundError):
            watch_dir = _require_config_path(self.__namer_config, 'watch_dir')
            for file in watch_dir.rglob('**/*.*'):
                resolved_file = file.resolve()
                if not _path_is_within(watch_dir, resolved_file):
                    logger.error('file should be in watch dir {}', resolved_file)
                    continue

                relative_path = str(resolved_file.relative_to(watch_dir))
                if not self.__namer_config.ignored_dir_regex.search(relative_path) and is_interesting_movie(resolved_file, self.__namer_config) and done_copying(resolved_file):
                    self.__event_handler.prepare_file_for_processing(resolved_file)

    def stop(self):
        """
        stops a background thread to check for files.
        Waits for the event processor to complete.
        """
        if not self.__stopped:
            self.__stopped = True
            logger.debug('Exiting watchdog')

            self.__event_observer.stop()
            logger.debug('Observer stop')

            self.__event_observer.join()
            logger.debug('Observer join')

            if self.__webserver:
                logger.info('Webserver stop')
                self.__webserver.stop()

            self.__command_queue.put(None)

            # let the thread processing work items complete.
            self.__worker_thread.join()
            logger.debug('Command queue None')

            test = os.environ.get('PYTEST_CURRENT_TEST', '')
            logger.debug(f'{test}: Command join')

            items = list(map(lambda x: x.get_command_target() if x else None, self.__command_queue.queue))
            logger.info(f'Waiting for items to process {items}')
            # we already wait for the worker thread.
            # self.__command_queue.join()
            logger.debug('Command joined')

    def get_web_port(self) -> Optional[int]:
        if self.__webserver is not None:
            return self.__webserver.get_effective_port()

        return None

    def __schedule(self):
        self.__event_observer.schedule(self.__event_handler, str(self.__src_path), recursive=True)


def create_watcher(namer_watchdog_config: NamerConfig) -> MovieWatcher:
    """
    Configure and start a watchdog looking for new Movies.
    """
    logger.info(namer_watchdog_config)

    if not verify_configuration(namer_watchdog_config, PartialFormatter()):
        sys.exit(-1)

    user = get_user_info(namer_watchdog_config)
    if not user:
        sys.exit(-1)

    logger.info('Logged as {name} ({id})'.format(**user))

    if namer_watchdog_config.retry_time:
        schedule.every().day.at(namer_watchdog_config.retry_time).do(lambda: retry_failed(namer_watchdog_config))

    movie_watcher = MovieWatcher(namer_watchdog_config)

    return movie_watcher


def main(config: NamerConfig):
    level = 'DEBUG' if config.debug else 'INFO'
    logger.add(sys.stdout, format=config.console_format, level=level, diagnose=config.diagnose_errors)

    # Optional file logging via shared helper
    setup_file_logging(config)

    create_watcher(config).run()
