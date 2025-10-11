import argparse
import sys
from pathlib import Path
from typing import List

from loguru import logger

from namer.configuration_utils import default_config
from namer.namer import calculate_phash


def main(args_list: List[str]):
    """
    Command line interface to calculate hashes for a file.
    """
    description = """
    Command line interface to calculate hashes for a file
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--configfile', help='override location for a configuration file.', type=Path)
    parser.add_argument('-f', '--file', help='File we want to provide a match name for.', required=True, type=Path)
    parser.add_argument('-v', '--verbose', help='verbose, print logs', action='store_true')
    args = parser.parse_args(args=args_list)

    config = default_config(args.configfile.resolve() if args.configfile else None)
    if args.verbose:
        level = 'DEBUG' if config.debug else 'INFO'
        logger.add(sys.stdout, format=config.console_format, level=level, diagnose=config.diagnose_errors)

    try:
        file_hash = calculate_phash(args.file.resolve(), config)
        if file_hash is None:
            logger.error('Unable to calculate perceptual hash for %s: no hash returned', args.file)
            sys.exit(1)
        print(file_hash.to_dict())
    except FileNotFoundError:
        logger.error('File not found: %s', args.file)
        sys.exit(1)
    except Exception as e:
        logger.error('Error calculating perceptual hash for %s: %s', args.file, e)
        if config.diagnose_errors:
            raise
        sys.exit(1)
