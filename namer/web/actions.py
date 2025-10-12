"""
Helper functions to tie in to namer's functionality.
"""

import json
import gzip
import math
import shutil
from enum import Enum
from functools import lru_cache
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import orjson  # type: ignore[import]  # Optional dependency for performance
    HAS_ORJSON = True
except ImportError:  # pragma: no cover - optional dependency
    orjson = None  # type: ignore[assignment]
    HAS_ORJSON = False

import jsonpickle  # type: ignore[import]  # No type stubs available
from werkzeug.routing import Rule

from namer.comparison_results import ComparisonResults, SceneType
from namer.configuration import NamerConfig
from namer.command import gather_target_files_from_dir, is_interesting_movie, is_relative_to, Command
from namer.fileinfo import FileInfo, parse_file_name
from namer.metadataapi import __evaluate_match, __metadataapi_response_to_data
from namer.namer import calculate_phash
from namer.videophash import PerceptualHash
from namer.metadata_providers.factory import get_metadata_provider


def _orjson_loads(value: str) -> Any:
    """Load JSON using orjson if available, otherwise use stdlib json."""
    if HAS_ORJSON:
        return orjson.loads(value)
    return json.loads(value)


def _orjson_dumps(value: Any, *, sort_keys: bool = False, indent: int = 2) -> str:
    """Dump JSON using orjson if available, otherwise use stdlib json."""
    if HAS_ORJSON:
        # orjson only supports indent=2 via OPT_INDENT_2; validate parameter
        if indent not in (0, 2):
            from loguru import logger
            logger.error('Invalid indent parameter for orjson: {}. Only 0 (no indent) or 2 are supported.', indent)
            raise ValueError(f'orjson only supports indent=0 or indent=2, got indent={indent}')

        option = 0
        if indent:
            option |= orjson.OPT_INDENT_2
        if sort_keys:
            option |= orjson.OPT_SORT_KEYS
        return orjson.dumps(value, option=option).decode('UTF-8')

    return json.dumps(value, sort_keys=sort_keys, indent=indent if indent else None)


class SearchType(str, Enum):
    ANY = 'Any'
    SCENES = 'Scenes'
    MOVIES = 'Movies'
    JAV = 'JAV'


def _require_path(path: Optional[Path], name: str) -> Path:
    if path is None:
        raise ValueError(f'NamerConfig.{name} must be configured')
    return path


def has_no_empty_params(rule: Rule) -> bool:
    """
    Currently unused, useful to inspect Flask rules.
    """
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


def get_failed_files(config: NamerConfig) -> List[Dict]:
    """
    Get failed files to rename.
    """
    failed_dir = _require_path(config.failed_dir, 'failed_dir')
    return [command_to_file_info(o, config) for o in gather_target_files_from_dir(failed_dir, config)]


def get_queued_files(queue: Queue, config: NamerConfig, queue_limit: int = 100) -> List[Dict]:
    """
    Get queued files.
    """
    queue_items = list(queue.queue)[:queue_limit]
    return [command_to_file_info(x, config) for x in queue_items if x is not None]


def get_queue_size(queue: Queue) -> int:
    return queue.qsize()


def command_to_file_info(command: Command, config: NamerConfig) -> Dict:
    stat = command.target_movie_file.stat()
    failed_dir = _require_path(command.config.failed_dir, 'failed_dir')

    sub_path = None
    if is_relative_to(command.target_movie_file, failed_dir):
        sub_path = str(command.target_movie_file.resolve().relative_to(failed_dir.resolve()))

    res: Dict[str, Any] = {
        'file': sub_path,
        'name': command.target_directory.stem if command.parsed_dir_name and command.target_directory else command.target_movie_file.stem,
        'ext': command.target_movie_file.suffix[1:].upper(),
        'update_time': int(stat.st_mtime),
        'size': stat.st_size,
    }

    percentage, phash, oshash = 0.0, '', ''
    if config.write_namer_failed_log and config.add_columns_from_log and sub_path:
        log_data = read_failed_log_file(sub_path, config)
        if log_data:
            if log_data.results:
                percentage = max([100 - item.phash_distance * 2.5 if item.phash_distance is not None and item.phash_distance <= 8 else item.name_match for item in log_data.results])

            if log_data.fileinfo and log_data.fileinfo.hashes:
                phash = str(log_data.fileinfo.hashes.phash)
                oshash = log_data.fileinfo.hashes.oshash

    res['percentage'] = percentage
    res['phash'] = phash
    res['oshash'] = oshash

    log_time = 0
    if config.add_complete_column and config.write_namer_failed_log and sub_path:
        log_file = command.target_movie_file.parent / (command.target_movie_file.stem + '_namer.json.gz')
        if log_file.is_file():
            log_stat = log_file.stat()
            log_time = int(log_stat.st_ctime)

    res['log_time'] = log_time

    return res


def metadataapi_responses_to_webui_response(responses: Dict, config: NamerConfig, file: str, phash: Optional[PerceptualHash] = None) -> List:
    file_path = Path(file)
    file_name = file_path.stem
    if not file_path.suffix and config.target_extensions:
        file_name += '.' + config.target_extensions[0]

    file_infos = []
    for url, response in responses.items():
        if response and response.strip() != '':
            json_obj = _orjson_loads(response)
            formatted = _orjson_dumps(json_obj, sort_keys=True)
            name_parts = parse_file_name(file_name, config)
            file_infos.extend(__metadataapi_response_to_data(json_obj, url, formatted, name_parts, config))

    files = []
    for scene_data in file_infos:
        fallback_source = scene_data.name or file_name
        parsed_name_parts: FileInfo = scene_data.original_parsed_filename or parse_file_name(fallback_source, config)

        scene = __evaluate_match(parsed_name_parts, scene_data, config, phash).as_dict()
        scene.update(
            {
                'name_parts': parsed_name_parts,
                'looked_up': {
                    'uuid': scene_data.uuid,
                    'type': scene_data.type.value if scene_data.type else SceneType.SCENE.value,
                    'name': scene_data.name,
                    'date': scene_data.date,
                    'poster_url': scene_data.poster_url,
                    'site': scene_data.site,
                    'network': scene_data.network,
                    'performers': scene_data.performers,
                },
            }
        )
        files.append(scene)

    return files


def get_search_results(query: str, search_type: SearchType, file: str, config: NamerConfig, page: int = 1) -> Dict:
    """
    Search results for user selection using the configured metadata provider.
    """
    provider = get_metadata_provider(config)
    all_results = []

    # Search different content types based on search_type
    if search_type == SearchType.ANY or search_type == SearchType.SCENES:
        scene_results = provider.search(query, SceneType.SCENE, config, page)
        all_results.extend(scene_results)

    if search_type == SearchType.ANY or search_type == SearchType.MOVIES:
        movie_results = provider.search(query, SceneType.MOVIE, config, page)
        all_results.extend(movie_results)

    if search_type == SearchType.ANY or search_type == SearchType.JAV:
        jav_results = provider.search(query, SceneType.JAV, config, page)
        all_results.extend(jav_results)

    # Convert LookedUpFileInfo objects to web UI format
    files = []
    for scene_data in all_results:
        # Parse the file name for comparison
        name_parts = parse_file_name(query, config)

        # Create a basic comparison result for the web UI
        scene = {
            'name_parts': name_parts,
            'looked_up': {
                'uuid': scene_data.uuid,
                'type': scene_data.type.value if scene_data.type else 'SCENE',
                'name': scene_data.name,
                'date': scene_data.date,
                'poster_url': scene_data.poster_url,
                'site': scene_data.site,
                'network': scene_data.network,
                'performers': scene_data.performers,
            },
            # Add basic matching scores (simplified for now)
            'name_match': 0.0,
            'date_match': False,
            'site_match': False,
            'phash_distance': None,
            'phash_duration': None,
        }
        files.append(scene)

    return {
        'file': file,
        'files': files,
    }


def get_phash_results(file: str, _search_type: SearchType, config: NamerConfig) -> Dict:
    """
    Search results by phash for user selection using the configured metadata provider.
    """
    failed_dir = _require_path(config.failed_dir, 'failed_dir')
    phash_file = failed_dir / file
    if not phash_file.is_file():
        return {'file': file, 'files': []}

    phash = calculate_phash(phash_file, config)
    if not phash:
        return {'file': file, 'files': []}

    provider = get_metadata_provider(config)

    # Use the provider's match function with phash for better results
    name_parts = parse_file_name(file, config)
    comparison_results = provider.match(name_parts, config, phash)

    # Convert ComparisonResults to web UI format
    files = []
    for result in comparison_results.results:
        scene = {
            'name_parts': result.name_parts,
            'looked_up': {
                'uuid': result.looked_up.uuid,
                'type': result.looked_up.type.value if result.looked_up.type else 'SCENE',
                'name': result.looked_up.name,
                'date': result.looked_up.date,
                'poster_url': result.looked_up.poster_url,
                'site': result.looked_up.site,
                'network': result.looked_up.network,
                'performers': result.looked_up.performers,
            },
            'name_match': result.name_match,
            'date_match': result.date_match,
            'site_match': result.site_match,
            'phash_distance': result.phash_distance,
            'phash_duration': result.phash_duration,
        }
        files.append(scene)

    return {
        'file': file,
        'files': files,
    }


def delete_file(file_name_str: str, config: NamerConfig) -> bool:
    """
    Delete selected file.
    """
    failed_dir = _require_path(config.failed_dir, 'failed_dir')
    file_name = failed_dir / file_name_str
    if not is_acceptable_file(file_name, config) or not config.allow_delete_files:
        return False

    if config.del_other_files and file_name.is_dir():
        target_name = failed_dir / Path(file_name_str).parts[0]
        shutil.rmtree(target_name)
    else:
        log_file = failed_dir / (file_name.stem + '_namer.json.gz')
        if log_file.is_file():
            log_file.unlink()

        file_name.unlink()

    return not file_name.is_file()


def read_failed_log_file(name: str, config: NamerConfig) -> Optional[ComparisonResults]:
    failed_dir = _require_path(config.failed_dir, 'failed_dir')
    file = failed_dir / name
    file = file.parent / (file.stem + '_namer.json.gz')

    res: Optional[ComparisonResults] = None
    if file.is_file():
        res = _read_failed_log_file(file, file.stat().st_size, file.stat().st_mtime)

    return res


@lru_cache(maxsize=1024)
def _read_failed_log_file(file: Path, _file_size: int, _file_update: float) -> Optional[ComparisonResults]:
    res: Optional[ComparisonResults] = None
    if file.is_file():
        data = gzip.decompress(file.read_bytes())
        decoded = jsonpickle.decode(data)
        if decoded and isinstance(decoded, ComparisonResults):
            for item in decoded.results:
                if not hasattr(item, 'phash_distance'):
                    item.phash_distance = 0 if hasattr(item, 'phash_match') and getattr(item, 'phash_match') else None  # noqa: B009

                if not hasattr(item, 'phash_duration'):
                    item.phash_duration = None

                if not hasattr(item.looked_up, 'hashes'):
                    item.looked_up.hashes = []

                if item.looked_up.performers:
                    for performer in item.looked_up.performers:
                        if not hasattr(performer, 'alias'):
                            performer.alias = None

            if not hasattr(decoded, 'fileinfo'):
                decoded.fileinfo = FileInfo()

            res = decoded

    return res


def is_acceptable_file(file: Path, config: NamerConfig) -> bool:
    """
    Checks if a file belong to namer.
    """
    return str(config.failed_dir) in str(file.resolve()) and file.is_file() and is_interesting_movie(file, config)


def human_format(num):
    if num == 0:
        return '0'

    size = 1000
    size_name = ('', 'K', 'M', 'B', 'T')
    i = int(math.floor(math.log(num, size)))
    p = math.pow(size, i)
    s = str(round(num / p, 2))
    s = s.rstrip('0').rstrip('.')

    return f'{s}{size_name[i]}'
