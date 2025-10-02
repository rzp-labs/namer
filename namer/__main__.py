"""
Namer, the porn db file renamer. It can be a command line tool to rename mp4/mkv/avi/mov/flv files and to embed tags in mp4's,
or a watchdog service to do the above watching a directory for new files.  File names are assumed to be of
the form SITE.[YY]YY.MM.DD.String.of.performers.and.or.scene.name.<IGNORED_INFO>.[mp4|mkv|...].   In the name, read the
periods, ".", as any number of spaces " ", dashes "-", or periods ".".

Provided you have an access token to the porndb (free sign up) https://www.theporndb.net/, this program will
attempt to match your file's name to search results from the porndb.   Please note that the site must at least be
a substring of the actual site name on the porndb, and the date must be within one day or the release date on the
porndb for a match to be considered.  If the log file flag is enabled then a <original file name minus ext>_namer.json.gz
file will be written with all the potential matches sorted, descending by how closely the scene name/performer names
match the file.
"""

import sys
import argparse
from datetime import timedelta
from pathlib import Path

from loguru import logger
from requests_cache import CachedSession

import namer.metadataapi
import namer.namer
import namer.videohashes
import namer.watchdog
import namer.web
from namer.configuration_utils import default_config
from namer.models import db, File
from pony.orm import db_session, select

DESCRIPTION = (
    namer.namer.DESCRIPTION
    + """

    The first argument should be 'watchdog', 'rename', 'suggest', or 'help' to see this message, for more help on rename, call
    namer 'namer rename -h'

    watchdog and help take no arguments (please see the config file example https://github.com/ThePornDatabase/namer/blob/main/namer/namer.cfg.default)

    'suggest' takes a file name as input and will output a suggested file name.
    'url' print url to namer web ui.
    'hash' takes a file name as input and will output a hashes in json format.
    'clear-cache' clears cached hashes for files matching a pattern (forces recalculation).
    """
)


def create_default_config_if_missing():
    """
    Find or create config.
    """
    config_file = Path('.namer.conf')
    print('Creating default config file here: {}', config_file)
    print('please edit the token or any other settings whose defaults you want changed.')


def main():
    """
    Call main method in namer.namer or namer.watchdog.
    """
    logger.remove()

    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-c', '--config', help='Path to a namer.cfg file.')
    args, arg_list = conf_parser.parse_known_args()

    config_file = Path(args.config) if args.config else None
    config = default_config(config_file)

    # create a CachedSession objects for request caching.
    if config.use_requests_cache:
        cache_file = config.database_path / 'namer_cache'
        expire_time = timedelta(minutes=config.requests_cache_expire_minutes)
        config.cache_session = CachedSession(str(cache_file), backend='sqlite', expire_after=expire_time, ignored_parameters=['Authorization'])

    if config.use_database:
        db_file = config.database_path / 'namer_database.sqlite'
        db.bind(provider='sqlite', filename=str(db_file), create_db=True)
        db.generate_mapping(create_tables=True)

    arg1 = None if len(arg_list) == 0 else arg_list[0]
    if arg1 == 'watchdog':
        namer.watchdog.main(config)
    elif arg1 == 'rename':
        namer.namer.main(arg_list[1:])
    elif arg1 == 'suggest':
        namer.metadataapi.main(arg_list[1:])
    elif arg1 == 'url':
        print(f'http://{config.host}:{config.port}{config.web_root}')
    elif arg1 == 'hash':
        namer.videohashes.main(arg_list[1:])
    elif arg1 == 'clear-cache':
        clear_hash_cache(arg_list[1:])
    elif arg1 in ['-h', 'help', None]:
        print(DESCRIPTION)

    if config.use_requests_cache and config.cache_session:
        config.cache_session.cache.delete(expired=True)


def clear_hash_cache(arg_list):
    """Clear cached hashes for files matching a pattern."""
    if len(arg_list) == 0:
        print('Usage: namer clear-cache <filename_pattern>')
        print('Example: namer clear-cache tushy.23.04.16.azul.hermosa')
        return

    filename_pattern = arg_list[0]
    config = default_config()

    if not config.use_database:
        print('❌ Database is not enabled in configuration')
        return

    db_file = config.database_path / 'namer_database.sqlite'
    if not db_file.exists():
        print('❌ Database file does not exist')
        return

    try:
        # Database should already be bound from main(), but ensure it's bound
        if not db.provider:
            db.bind(provider='sqlite', filename=str(db_file), create_db=False)
            db.generate_mapping()

        with db_session:
            # Find files matching the filename pattern
            files = select(f for f in File if filename_pattern.lower() in f.file_name.lower())[:]

            if not files:
                print(f'❌ No cached entries found for filename containing: {filename_pattern}')
                return

            print(f'🔍 Found {len(files)} cached entries:')
            for f in files:
                print(f'   📁 {f.file_name} (size: {f.file_size}, phash: {f.phash})')

            # Delete the entries
            for f in files:
                f.delete()
                print(f'🗑️  Deleted cache entry for: {f.file_name}')

            print('✅ Cache cleared successfully!')
            print('🔄 Next processing will recalculate hash with format consistency fixes')

    except Exception as e:
        print(f'❌ Error clearing cache: {e}')


if __name__ == '__main__':
    main()
