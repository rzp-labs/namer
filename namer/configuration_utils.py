"""
Namer Configuration readers/verifier
"""

import os
import random
import re
import shutil
from importlib import resources
from typing import Dict, List, Optional, Callable, Pattern, Any, Tuple
from configupdater import ConfigUpdater
from pathlib import Path

import orjson
from loguru import logger

from namer import database
from namer.configuration import NamerConfig
from namer.ffmpeg import FFMpeg
from namer.name_formatter import PartialFormatter


def __verify_naming_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error('Since enable_metadataapi_genres is not True, you must specify a default_genre')
        success = False

    success = __verify_name_string(formatter, 'inplace_name', config.inplace_name) and success

    if config.inplace_name_scene:
        success = __verify_name_string(formatter, 'inplace_name_scene', config.inplace_name_scene) and success

    if config.inplace_name_movie:
        success = __verify_name_string(formatter, 'inplace_name_movie', config.inplace_name_movie) and success

    if config.inplace_name_jav:
        success = __verify_name_string(formatter, 'inplace_name_jav', config.inplace_name_jav) and success

    return success


def validate_disambiguation_config(config: NamerConfig) -> bool:
    """
    Validate relationships for disambiguation thresholds. Returns True when valid.
    This function is intentionally lightweight and does not raise.
    """
    ok = True
    # Majority fraction range
    if not (0.0 <= config.phash_majority_accept_fraction <= 1.0):
        logger.error(
            'phash_majority_accept_fraction must be within [0.0, 1.0], got {}',
            config.phash_majority_accept_fraction,
        )
        ok = False
    # Distance relationships
    if config.phash_accept_distance >= config.phash_ambiguous_min:
        logger.error(
            'phash_accept_distance ({}) must be less than phash_ambiguous_min ({})',
            config.phash_accept_distance,
            config.phash_ambiguous_min,
        )
        ok = False
    if config.phash_ambiguous_min > config.phash_ambiguous_max:
        logger.error(
            'phash_ambiguous_min ({}) must be less than or equal to phash_ambiguous_max ({})',
            config.phash_ambiguous_min,
            config.phash_ambiguous_max,
        )
        ok = False
    if config.phash_distance_margin_accept < 0:
        logger.error('phash_distance_margin_accept must be >= 0, got {}', config.phash_distance_margin_accept)
        ok = False

    return ok


def __verify_watchdog_config(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Verifies the contents of your config file. Returns False if configuration failed.
    """
    success = True
    if not config.enable_metadataapi_genres and not config.default_genre:
        logger.error('Since enable_metadataapi_genres is not True, you must specify a default_genre')
        success = False

    watchdog_dirs = ['watch_dir', 'work_dir', 'failed_dir', 'dest_dir', 'ambiguous_dir']
    for dir_name in watchdog_dirs:
        success = __verify_dir(config, dir_name, [name for name in watchdog_dirs if dir_name != name]) and success

    success = __verify_name_string(formatter, 'new_relative_path_name', config.new_relative_path_name) and success

    if config.new_relative_path_name_scene:
        success = __verify_name_string(formatter, 'new_relative_path_name_scene', config.new_relative_path_name_scene) and success

    if config.new_relative_path_name_movie:
        success = __verify_name_string(formatter, 'new_relative_path_name_movie', config.new_relative_path_name_movie) and success

    if config.new_relative_path_name_jav:
        success = __verify_name_string(formatter, 'new_relative_path_name_jav', config.new_relative_path_name_jav) and success

    return success


def __verify_dir(config: NamerConfig, name: str, other_dirs: List[str]) -> bool:
    """
    Verify a configured directory. Returns False if verification fails.
    Special-case 'ambiguous_dir' to allow non-existent path (created later at runtime),
    while still guarding against nesting within other watchdog directories.
    """
    path_list = tuple(str(getattr(config, n)) for n in other_dirs if hasattr(config, n))
    dir_name: Optional[Path] = getattr(config, name) if hasattr(config, name) else None

    if dir_name:
        dir_str = str(dir_name)
        is_nested = dir_str.startswith(path_list) if path_list else False
        exists = dir_name.exists()

        if name == 'ambiguous_dir':
            # Allow non-existent ambiguous_dir (it will be created at runtime),
            # but still forbid nesting within other watchdog directories.
            if is_nested:
                logger.error(f'Configured directory {name}: "{dir_name}" must not be inside another watchdog directory')
                return False
            if exists and not dir_name.is_dir():
                logger.error(f'Configured directory {name}: "{dir_name}" exists but is not a directory')
                return False
        else:
            # For all other watchdog dirs, require existing directory and no nesting
            if (not dir_name.is_dir()) or is_nested:
                logger.error(f'Configured directory {name}: "{dir_name}" is not a directory or is inside another watchdog directory')
                return False

        # work_dir should be empty only if it exists
        min_size = config.min_file_size if config.min_file_size else 1
        if name == 'work_dir' and exists:
            total_mb = sum(file.stat().st_size for file in dir_name.rglob('*')) / 1024 / 1024
            if total_mb > min_size:
                logger.error(f'Configured directory {name}: "{dir_name}" should be empty')
                return False

        # Warn about permissions only when the path exists
        if exists and not os.access(dir_name, os.W_OK):
            logger.warning(f'Configured directory {name}: "{dir_name}" might have write permission problem')

    return True


def __verify_name_string(formatter: PartialFormatter, name: str, name_string: str) -> bool:
    """
    Verify the name format string.
    """
    values = dict(zip(formatter.supported_keys, formatter.supported_keys))
    try:
        formatter.format(name_string, values)
        return True
    except KeyError as key_error:
        logger.error('Configuration {} is not a valid file name format, please check {}', name, name_string)
        logger.error('Error message: {}', key_error)
        return False


def __verify_ffmpeg(ffmpeg: FFMpeg) -> bool:
    versions = ffmpeg.ffmpeg_version()
    for tool, version in versions.items():
        if not version:
            logger.error(f'No {tool} found, please install {tool}')
        else:
            logger.info(f'{tool} version "{version}" found')

    return None not in versions.values()


def __verify_metadata_provider_config(config: NamerConfig) -> bool:
    """
    Verify metadata provider configuration settings.
    """
    success = True

    # Validate provider selection
    supported_providers = ['theporndb', 'stashdb']
    if config.metadata_provider.lower() not in supported_providers:
        logger.error(f'Unsupported metadata provider: "{config.metadata_provider}". Supported: {supported_providers}')
        success = False

    # Only validate provider-specific settings if directories are configured (indicates real usage vs test)
    if hasattr(config, 'watch_dir') or hasattr(config, 'dest_dir') or hasattr(config, 'work_dir'):
        # Validate provider-specific settings for real configurations
        if config.metadata_provider.lower() == 'theporndb':
            if not config.porndb_token or config.porndb_token.strip() == '':
                logger.error('ThePornDB provider requires a porndb_token. Sign up at https://theporndb.net/register')
                success = False
            # Endpoint is built-in; override is optional and primarily used by tests
            if not config.override_tpdb_address:
                logger.info('Using default ThePornDB endpoint; override_tpdb_address not set')

        elif config.metadata_provider.lower() == 'stashdb':
            # Endpoint is built-in; override is optional and primarily used by advanced deployments
            if not config.stashdb_endpoint or config.stashdb_endpoint.strip() == '':
                logger.info('Using default StashDB endpoint; stashdb_endpoint not set')

            if not config.stashdb_token or config.stashdb_token.strip() == '':
                logger.warning('StashDB provider works better with an API token (stashdb_token)')
    else:
        # For test configurations without directories, just warn about missing tokens
        if config.metadata_provider.lower() == 'theporndb' and (not config.porndb_token or config.porndb_token.strip() == ''):
            logger.warning('ThePornDB provider would require a porndb_token in production')
        elif config.metadata_provider.lower() == 'stashdb' and (not config.stashdb_endpoint or config.stashdb_endpoint.strip() == ''):
            logger.warning('StashDB provider would require stashdb_endpoint in production')

    return success


def verify_configuration(config: NamerConfig, formatter: PartialFormatter) -> bool:
    """
    Can verify a NamerConfig with a formatter
    """
    success = __verify_naming_config(config, formatter)
    success = __verify_watchdog_config(config, formatter) and success
    success = __verify_ffmpeg(config.ffmpeg) and success
    success = __verify_metadata_provider_config(config) and success

    if config.image_format not in ['jpeg', 'png'] and success:
        logger.error('image_format should be png or jpeg')
        success = False

    # Disambiguation thresholds sanity
    success = validate_disambiguation_config(config) and success

    return success


# Read and write .ini files utils below


def get_str(updater: ConfigUpdater, section: str, key: str) -> Optional[str]:
    """
    Read a string from an ini file if the config exists, else return None if the config does not
    exist in file.
    """
    if updater.has_option(section, key):
        output = updater.get(section, key)
        return str(output.value) if output.value else output.value

    return None


# Ini file string converters, to and from NamerConfig type


def to_bool(value: Optional[str]) -> Optional[bool]:
    return value.lower() == 'true' if value else None


def from_bool(value: Optional[bool]) -> str:
    return str(value) if value is not None else ''


def to_str_list_lower(value: Optional[str]) -> List[str]:
    return [x.strip().lower() for x in value.lower().split(',')] if value else []


def from_str_list_lower(value: Optional[List[str]]) -> str:
    return ', '.join(value) if value else ''


def to_int(value: Optional[str]) -> Optional[int]:
    return int(value) if value is not None else None


def from_int(value: Optional[int]) -> str:
    return str(value) if value is not None else ''


def to_path(value: Optional[str]) -> Optional[Path]:
    return Path(value).resolve() if value else None


def from_path(value: Optional[Path]) -> str:
    return str(value) if value else ''


def to_float(value: Optional[str]) -> Optional[float]:
    return float(value) if value is not None else None


def from_float(value: Optional[float]) -> str:
    return str(value) if value is not None else ''


def to_regex_list(value: Optional[str]) -> List[Pattern]:
    return [re.compile(x.strip()) for x in value.split(',')] if value else []


def from_regex_list(value: Optional[List[Pattern]]) -> str:
    return ', '.join([x.pattern for x in value]) if value else ''


def to_site_abbreviation(site_abbreviations: Optional[str]) -> Dict[Pattern, str]:
    abbreviations_db = database.abbreviations.copy()
    if site_abbreviations:
        data = orjson.loads(site_abbreviations)
        abbreviations_db.update(data)

    new_abbreviation: Dict[Pattern, str] = {}
    for abbreviation, full in abbreviations_db.items():
        key = re.compile(rf'^{abbreviation}[ .-]+', re.IGNORECASE)
        new_abbreviation[key] = f'{full} '

    return new_abbreviation


def from_site_abbreviation(site_abbreviations: Optional[Dict[Pattern, str]]) -> str:
    out: Dict[str, str] = {x.pattern[1:-6]: y[0:-1] for (x, y) in site_abbreviations.items()} if site_abbreviations else {}
    res = orjson.dumps(out).decode('UTF-8')

    return res


def to_pattern(value: Optional[str]) -> Optional[Pattern]:
    return re.compile(value, re.IGNORECASE) if value else None


def from_pattern(value: Optional[Pattern]) -> str:
    return value.pattern if value else ''


def to_site_list(value: Optional[str]) -> List[str]:
    return [re.sub(r'[^a-z0-9]', '', x.strip().lower()) for x in value.split(',')] if value else []


def set_str(updater: ConfigUpdater, section: str, key: str, value: str) -> None:
    updater[section][key].value = value


def set_comma_list(updater: ConfigUpdater, section: str, key: str, value: List[str]) -> None:
    updater[section][key].value = ', '.join(value)


def set_int(updater: ConfigUpdater, section: str, key: str, value: int) -> None:
    updater[section][key].value = str(value)


def set_boolean(updater: ConfigUpdater, section: str, key: str, value: bool) -> None:
    updater[section][key] = str(value)


field_info: Dict[str, Tuple[str, Optional[Callable[[Optional[str]], Any]], Optional[Callable[[Any], str]]]] = {
    'porndb_token': ('namer', None, None),
    'name_parser': ('namer', None, None),
    'inplace_name': ('namer', None, None),
    'inplace_name_scene': ('namer', None, None),
    'inplace_name_movie': ('namer', None, None),
    'inplace_name_jav': ('namer', None, None),
    'prefer_dir_name_if_available': ('namer', to_bool, from_bool),
    'min_file_size': ('namer', to_int, from_int),
    'write_namer_log': ('namer', to_bool, from_bool),
    'write_namer_failed_log': ('namer', to_bool, from_bool),
    'target_extensions': ('namer', to_str_list_lower, from_str_list_lower),
    'update_permissions_ownership': ('namer', to_bool, from_bool),
    'set_dir_permissions': ('namer', to_int, from_int),
    'set_file_permissions': ('namer', to_int, from_int),
    'set_uid': ('namer', to_int, from_int),
    'set_gid': ('namer', to_int, from_int),
    'trailer_location': ('namer', None, None),
    'convert_container_to': ('namer', None, None),
    'sites_with_no_date_info': ('namer', to_str_list_lower, from_str_list_lower),
    'movie_data_preferred': ('namer', to_str_list_lower, from_str_list_lower),
    'vr_studios': ('namer', to_str_list_lower, from_str_list_lower),
    'vr_tags': ('namer', to_str_list_lower, from_str_list_lower),
    'site_abbreviations': ('namer', to_site_abbreviation, from_site_abbreviation),
    'max_performer_names': ('namer', to_int, from_int),
    'use_database': ('namer', to_bool, from_bool),
    'database_path': ('namer', to_path, from_path),
    'use_requests_cache': ('namer', to_bool, from_bool),
    'requests_cache_expire_minutes': ('namer', to_int, from_int),
    'metadata_provider': ('namer', None, None),
    'override_tpdb_address': ('namer', None, None),
    'stashdb_endpoint': ('namer', None, None),
    'stashdb_token': ('namer', None, None),
    'plex_hack': ('namer', to_bool, from_bool),
    'path_cleanup': ('namer', to_bool, from_bool),
    # Disambiguation gating and thresholds
    'enable_disambiguation': ('namer', to_bool, from_bool),
    'search_phash': ('Phash', to_bool, from_bool),
    'send_phash': ('Phash', to_bool, from_bool),
    'use_alt_phash_tool': ('Phash', to_bool, from_bool),
    'phash_accept_distance': ('Phash', to_int, from_int),
    'phash_ambiguous_min': ('Phash', to_int, from_int),
    'phash_ambiguous_max': ('Phash', to_int, from_int),
    'phash_distance_margin_accept': ('Phash', to_int, from_int),
    'phash_majority_accept_fraction': ('Phash', to_float, from_float),
    'max_ffmpeg_workers': ('Phash', to_int, from_int),
    'use_gpu': ('Phash', to_bool, from_bool),
    'ffmpeg_hwaccel_backend': ('Phash', None, None),
    'ffmpeg_hwaccel_device': ('Phash', None, None),
    'ffmpeg_hwaccel_decoder': ('Phash', None, None),
    'mark_collected': ('metadata', to_bool, from_bool),
    'write_nfo': ('metadata', to_bool, from_bool),
    'enabled_tagging': ('metadata', to_bool, from_bool),
    'enabled_poster': ('metadata', to_bool, from_bool),
    'download_type': ('metadata', to_str_list_lower, from_str_list_lower),
    'image_format': ('metadata', None, None),
    'enable_metadataapi_genres': ('metadata', to_bool, from_bool),
    'default_genre': ('metadata', None, None),
    'language': ('metadata', None, None),
    'preserve_duplicates': ('duplicates', to_bool, from_bool),
    'max_desired_resolutions': ('duplicates', to_int, from_int),
    'desired_codec': ('duplicates', to_str_list_lower, from_str_list_lower),
    'ignored_dir_regex': ('watchdog', to_pattern, from_pattern),
    'del_other_files': ('watchdog', to_bool, from_bool),
    'extra_sleep_time': ('watchdog', to_int, from_int),
    'queue_limit': ('watchdog', to_int, from_int),
    'queue_sleep_time': ('watchdog', to_int, from_int),
    'new_relative_path_name': ('watchdog', None, None),
    'new_relative_path_name_scene': ('watchdog', None, None),
    'new_relative_path_name_movie': ('watchdog', None, None),
    'new_relative_path_name_jav': ('watchdog', None, None),
    'watch_dir': ('watchdog', to_path, from_path),
    'work_dir': ('watchdog', to_path, from_path),
    'failed_dir': ('watchdog', to_path, from_path),
    'dest_dir': ('watchdog', to_path, from_path),
    'ambiguous_dir': ('watchdog', to_path, from_path),
    'retry_time': ('watchdog', None, None),
    'web': ('watchdog', to_bool, from_bool),
    'port': ('watchdog', to_int, from_int),
    'host': ('watchdog', None, None),
    'web_root': ('watchdog', None, None),
    'allow_delete_files': ('watchdog', to_bool, from_bool),
    'add_columns_from_log': ('watchdog', to_bool, from_bool),
    'add_complete_column': ('watchdog', to_bool, from_bool),
    'webhook_enabled': ('webhook', to_bool, from_bool),
    'webhook_url': ('webhook', None, None),
    'debug': ('watchdog', to_bool, from_bool),
    'console_format': ('watchdog', None, None),
    'manual_mode': ('watchdog', to_bool, from_bool),
    'diagnose_errors': ('watchdog', to_bool, from_bool),
}
"""
A mapping from NamerConfig field to ini file section - the ini property name and the field name
must be identical.   The conversion of string too and from functions are also provided here allowing
the conversion of types from NamerConfig to and from strings.   If the converters are not set then the
the string is unaltered.
"""


def to_ini(config: NamerConfig) -> str:
    updater = config.config_updater
    for name in field_info.keys():
        info = field_info.get(name)
        if info:
            section = info[0]
            if section:
                value = getattr(config, name)
                convert: Optional[Callable[[Any], str]] = info[2]
                if convert:
                    updater.get(section, name).value = convert(value)
                else:
                    updater.get(section, name).value = value

    return str(updater)


def from_config(config: ConfigUpdater, namer_config: NamerConfig) -> NamerConfig:
    """
    Given a config parser pointed at a namer.cfg file, return a NamerConfig with the file's parameters.
    """
    keys = field_info.keys()
    for name in keys:
        info = field_info.get(name)
        if info and info[0]:
            new_value = get_str(config, info[0], name)
            if new_value or not hasattr(namer_config, name):
                type_converter_lambda: Optional[Callable[[Optional[str]], Any]] = info[1]
                if type_converter_lambda:
                    setattr(namer_config, name, type_converter_lambda(new_value))
                else:
                    setattr(namer_config, name, new_value)

    if not hasattr(namer_config, 'retry_time') or namer_config.retry_time is None:
        setattr(namer_config, 'retry_time', f'03:{random.randint(0, 59):0>2}')  # noqa: B010

    return namer_config


def resource_file_to_str(package: str, file_name: str) -> str:
    config_str = ''
    if hasattr(resources, 'files'):
        config_str = resources.files(package).joinpath(file_name).read_text(encoding='UTF-8')
    elif hasattr(resources, 'read_text'):
        config_str = resources.read_text(package, file_name)

    return config_str


def copy_resource_to_file(package: str, file_name: str, output: Path) -> bool:
    if hasattr(resources, 'files'):
        with resources.files(package).joinpath(file_name).open('rb') as _bin, open(output, mode='+bw') as out:
            shutil.copyfileobj(_bin, out)
            return True
    elif hasattr(resources, 'read_text'):
        with resources.open_binary(package, file_name) as _bin, open(output, mode='+bw') as out:
            shutil.copyfileobj(_bin, out)
            return True

    return False


def default_config(user_set: Optional[Path] = None) -> NamerConfig:
    """
    Attempts reading various locations to fine a namer.cfg file.
    """
    config = ConfigUpdater(allow_no_value=True)
    config_str = resource_file_to_str('namer', 'namer.cfg.default')
    config.read_string(config_str)
    namer_config = from_config(config, NamerConfig())
    namer_config.config_updater = config

    user_config = ConfigUpdater(allow_no_value=True)
    cfg_paths = [
        user_set,
        os.environ.get('NAMER_CONFIG'),
        Path.home() / '.namer.cfg',
        '.namer.cfg',
    ]

    for file in cfg_paths:
        if not file:
            continue

        if isinstance(file, str):
            file = Path(file)

        if file.is_file():
            user_config.read(file, encoding='UTF-8')
            break

    cfg = from_config(user_config, namer_config)

    # Environment overrides for sensitive tokens (do not require committing secrets)
    # Use TPDB_TOKEN for ThePornDB
    tpdb_env = os.environ.get('TPDB_TOKEN')
    if tpdb_env:
        setattr(cfg, 'porndb_token', tpdb_env)
    # Use STASHDB_TOKEN for StashDB
    stashdb_env = os.environ.get('STASHDB_TOKEN')
    if stashdb_env:
        setattr(cfg, 'stashdb_token', stashdb_env)

    return cfg
