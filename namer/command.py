"""
Tools for working with files and directories in namer.
"""

import argparse
import gzip
from dataclasses import dataclass
import os
import shutil
import sys
from pathlib import Path
from platform import system
from typing import Iterable, List, Optional, Sequence, Tuple

import jsonpickle
from loguru import logger

from namer.configuration import NamerConfig
from namer.configuration_utils import default_config
from namer.ffmpeg import FFProbeResults
from namer.fileinfo import parse_file_name, FileInfo
from namer.comparison_results import ComparisonResults, LookedUpFileInfo, SceneType


# noinspection PyDataclass
@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class Command:
    input_file: Path
    """
    This is the original user/machine input of a target path.
    If this path is a directory a movie is found within it (recursively).
    If this file is a the movie file itself, the parent directory is calculated.
    """
    target_movie_file: Path
    """
    The movie file this name is targeting.
    """
    target_directory: Optional[Path] = None
    """
    The containing directory of a File.  This may be the immediate parent directory, or higher up, depending
    on whether a directory was selected as the input to a naming process.
    """
    parsed_dir_name: bool
    """
    Was the input file a directory and is parsing directory names configured?
    """
    parsed_file: Optional[FileInfo] = None
    """
    The parsed file name.
    """

    inplace: bool = False
    """
    Was the command told to keep the files in place.
    """

    write_from_nfos: bool = False
    """
    Should .nfo files be used as a source of metadata and writen into file tag info and used for naming.
    """

    tpdb_id: Optional[str] = None
    """
    The _id used to identify video in tpdb
    """

    is_auto: bool = True
    """
    If False then it means command was from web ui
    """

    config: NamerConfig

    def get_command_target(self):
        return str(self.target_movie_file.resolve())


def move_command_files(target: Optional[Command], new_target: Path, is_auto: bool = True) -> Optional[Command]:
    """
    Move the movie file or containing directory described by a Command into a new destination and build a new Command for processing.
    
    If `target` is None this returns None. The function ensures `new_target` exists (returns None on failure), then:
    - if the Command's `input_file` equals its `target_directory`, moves the entire directory into `new_target` and builds a Command for the moved directory;
    - otherwise moves the single `target_movie_file` into `new_target` and builds a Command for the moved file.
    
    On success returns the newly created Command with `tpdb_id`, `inplace`, and `write_from_nfos` propagated from the original `target`. Filesystem moves and directory creation are performed as side effects.
    """
    if not target:
        return None

    # Ensure destination directory exists
    try:
        new_target.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f'Failed to create destination directory {new_target}: {e}')
        return None

    if target.target_directory and target.input_file == target.target_directory:
        working_dir = Path(new_target) / target.target_directory.name
        logger.info('Moving {} to {} for processing', target.target_directory, working_dir)
        shutil.move(target.target_directory, working_dir)
        output = make_command(working_dir, target.config, is_auto=is_auto)
    else:
        working_file = Path(new_target) / target.target_movie_file.name
        shutil.move(target.target_movie_file, working_file)
        logger.info('Moving {} to {} for processing', target.target_movie_file, working_file)
        output = make_command(working_file, target.config, is_auto=is_auto)

    if output:
        output.tpdb_id = target.tpdb_id
        output.inplace = target.inplace
        output.write_from_nfos = target.write_from_nfos

    return output


def _build_summary(match_attempts: Optional[ComparisonResults]) -> Optional[dict]:
    """
    Build a compact, JSON-serializable summary from ComparisonResults suitable for logging or small summary files.
    
    If match_attempts is falsy, returns None.
    
    Parameters:
        match_attempts (Optional[ComparisonResults]): ComparisonResults object containing ranked lookup results
            and an optional `ambiguous` flag. Only the following fields from each result are used:
            - result.looked_up: object with optional attributes `guid`, `uuid`, `name`, `site`, `date`
            - result.name, result.name_match, result.site_match, result.date_match
            - result.phash_distance, result.phash_duration
    
    Returns:
        Optional[dict]: A dictionary with the keys:
          - 'ambiguous' (bool): copied from match_attempts.
          - 'candidates' (list): flat, rank-ordered list of candidate dicts with keys
            ('rank','guid','uuid','title','site','date','name_match','site_match',
             'date_match','phash_distance','phash_duration').
          - 'groups' (list): grouped candidates by GUID with per-GUID stats:
            ('guid','title','site','date','count','min_phash_distance','has_duration_match').
          - 'summary_stats' (dict): top-level metrics including
            ('best_guid','best_min_phash_distance','second_min_phash_distance',
             'distance_margin','top_guid_fraction').
        Returns None when match_attempts is None or empty.
    
    Notes:
        - Numeric values are coerced to plain Python int/float where possible to ensure JSON compatibility.
        - GUID grouping ignores candidates without a GUID.
        - 'top_guid_fraction' is rounded to three decimal places when present.
    """
    if not match_attempts:
        return None
    # Prepare a compact, readable summary for humans
    summary: dict = {
        'ambiguous': getattr(match_attempts, 'ambiguous', False),
        'summary_stats': {},
        'groups': [],
        'candidates': [],
    }
    # Helpers to coerce potentially non-JSON-native numeric types
    def _to_int(val):
        """
        Convert a value to an int, returning None for None or if conversion fails.
        
        Parameters:
            val: Value to convert (any). If val is None, returns None.
        
        Returns:
            int or None: The integer conversion of val, or None if val is None or cannot be converted.
        """
        try:
            return int(val) if val is not None else None
        except Exception:
            return None
    def _to_float(val):
        """
        Convert a value to float, returning None for None or if conversion fails.
        
        Accepts numbers or strings; returns a float on successful conversion, otherwise None.
        """
        try:
            return float(val) if val is not None else None
        except Exception:
            return None
    # Flat candidates list (ranked as provided)
    for idx, result in enumerate(match_attempts.results or []):
        looked = result.looked_up
        summary['candidates'].append({
            'rank': idx + 1,
            'guid': getattr(looked, 'guid', None),
            'uuid': getattr(looked, 'uuid', None),
            'title': getattr(looked, 'name', None) or result.name,
            'site': getattr(looked, 'site', None),
            'date': getattr(looked, 'date', None),
            'name_match': getattr(result, 'name_match', None),
            'site_match': getattr(result, 'site_match', None),
            'date_match': getattr(result, 'date_match', None),
            'phash_distance': _to_int(getattr(result, 'phash_distance', None)),
            'phash_duration': getattr(result, 'phash_duration', None),
        })
    # Group by GUID to compute per-id stats
    from collections import defaultdict
    per_guid = defaultdict(list)
    for item in summary['candidates']:
        if item['guid']:
            per_guid[item['guid']].append(item)
    groups = []
    for guid, items in per_guid.items():
        distances = [i['phash_distance'] for i in items if i['phash_distance'] is not None]
        min_distance = _to_int(min(distances)) if distances else None
        any_duration_ok = any(bool(i['phash_duration']) for i in items)
        title = items[0]['title']
        site = items[0]['site']
        date = items[0]['date']
        groups.append({
            'guid': guid,
            'title': title,
            'site': site,
            'date': date,
            'count': _to_int(len(items)),
            'min_phash_distance': min_distance,
            'has_duration_match': any_duration_ok,
        })
    # Sort groups by min distance then count desc
    def _group_key(g):
        """
        Return a sort key for a group dictionary used to order candidate groups.
        
        The key is a tuple (min_phash_distance, -count) so groups with smaller phash
        distance sort first, and among equal distances groups with more members sort
        first. If 'min_phash_distance' is None it is treated as a very large value
        (9999) to place it after any real distances.
        
        Parameters:
            g (dict): Group dictionary containing at least 'min_phash_distance' and 'count'.
        
        Returns:
            tuple: (min_phash_distance_or_large_default, negative_count) suitable for sorting.
        """
        md = g['min_phash_distance']
        return (md if md is not None else 9999, -g['count'])
    groups.sort(key=_group_key)
    summary['groups'] = groups
    # Overall stats: best, second best, margin, majority fraction
    best = groups[0] if groups else None
    second = groups[1] if len(groups) > 1 else None
    best_d = _to_int(best['min_phash_distance']) if best else None
    second_d = _to_int(second['min_phash_distance']) if second else None
    margin = _to_int((second_d - best_d)) if (best_d is not None and second_d is not None) else None
    total_items = _to_int(sum(int(g['count']) for g in groups)) if groups else 0
    top_fraction = (_to_float(best['count'] / total_items) if (best and total_items) else None)
    summary['summary_stats'] = {
        'best_guid': best['guid'] if best else None,
        'best_min_phash_distance': best_d,
        'second_min_phash_distance': second_d,
        'distance_margin': margin,
        'top_guid_fraction': round(float(top_fraction), 3) if top_fraction is not None else None,
    }
    return summary


def write_log_file(movie_file: Optional[Path], match_attempts: Optional[ComparisonResults], namer_config: NamerConfig) -> Optional[Path]:
    """
    Write match attempt data to a compressed JSON log alongside an optional concise JSON summary.
    
    If movie_file is provided, this creates two files next to it:
    - "{stem}_namer.json.gz": a gzip-compressed jsonpickle dump of match_attempts with any
      sensitive lookup fields removed.
    - "{stem}_namer.summary.json": a compact JSON summary produced by _build_summary (written
      only if a summary can be built).
    
    Side effects:
    - Removes `original_query` and `original_response` from each result.looked_up before serialization.
    - Applies filesystem permissions/ownership from namer_config to any files written via set_permissions.
    - Logs failures to write the summary at debug level but does not raise.
    
    Parameters:
        movie_file: Path of the movie used to derive the log file names. If None, nothing is written.
        match_attempts: ComparisonResults to serialize; may be None.
        namer_config: Configuration used when applying permissions to created files.
    
    Returns:
        Path to the created compressed log file, or None if no log was written.
    """
    log_name = None
    if movie_file:
        log_name = movie_file.with_name(movie_file.stem + '_namer.json.gz')
        logger.info('Writing log to {}', log_name)
        with open(log_name, 'wb') as log_file:
            if match_attempts:
                for result in match_attempts.results:
                    del result.looked_up.original_query
                    del result.looked_up.original_response

            json_out = jsonpickle.encode(match_attempts, separators=(',', ':'))
            if json_out:
                json_out = json_out.encode('UTF-8')
                json_out = gzip.compress(json_out)
                log_file.write(json_out)

        set_permissions(log_name, namer_config)

        # Additionally write a concise summary for quick inspection
        try:
            summary = _build_summary(match_attempts)
            if summary is not None:
                summary_name = movie_file.with_name(movie_file.stem + '_namer.summary.json')  # type: ignore[arg-type]
                with open(summary_name, 'w', encoding='utf-8') as sfile:
                    import json
                    json.dump(summary, sfile, indent=2, ensure_ascii=False)
                set_permissions(summary_name, namer_config)
        except Exception as e:
            logger.debug(f'Failed to write summary log: {e}')

    return log_name


def _set_perms(target: Path, config: NamerConfig):
    file_perm: Optional[int] = int(str(config.set_file_permissions), 8) if config.set_file_permissions else None
    dir_perm: Optional[int] = int(str(config.set_dir_permissions), 8) if config.set_dir_permissions else None

    if config.set_gid or config.set_uid:
        os.lchown(target, uid=config.set_uid if config.set_uid else -1, gid=config.set_gid if config.set_gid else -1)

    if target.is_dir() and dir_perm:
        target.chmod(dir_perm)
    elif target.is_file() and file_perm:
        target.chmod(file_perm)


def set_permissions(file: Optional[Path], config: NamerConfig):
    """
    Given a file or dir, set permissions from NamerConfig.set_file_permissions,
    NamerConfig.set_dir_permissions, and uid/gid if set for the current process recursively.
    """
    if system() != 'Windows' and file and file.exists() and config.update_permissions_ownership:
        _set_perms(file, config)
        if file.is_dir():
            for target in file.rglob('**/*'):
                _set_perms(target, config)


def extract_relevant_attributes(ffprobe_results: Optional[FFProbeResults], config: NamerConfig) -> Tuple[float, int, int]:
    if not ffprobe_results:
        return 0, 0, 0

    stream = ffprobe_results.get_default_video_stream()
    if not stream:
        return 0, 0, 0

    return stream.duration, stream.height if stream.height else 0, get_codec_value(stream.codec_name.lower(), config)


def get_codec_value(codec: str, config: NamerConfig) -> int:
    desired_codecs = list(config.desired_codec)
    desired_codecs.reverse()
    if codec in desired_codecs:
        return desired_codecs.index(codec) + 1

    return 0


def greater_than(seq1: Sequence, seq2: Sequence) -> bool:
    for val in zip(seq1, seq2):
        if val[0] > val[1]:
            return True

        if val[0] == val[1]:
            continue
        else:
            return False

    return False  # equal


def selected_best_movie(movies: List[str], config: NamerConfig) -> Optional[Path]:
    # This could use a lot of work.
    if movies:
        selected = Path(movies[0])
        selected_values = extract_relevant_attributes(config.ffmpeg.ffprobe(selected), config)
        for current_movie_str in movies:
            current_movie = Path(current_movie_str)
            current_values = extract_relevant_attributes(config.ffmpeg.ffprobe(current_movie), config)
            if current_values[1] <= config.max_desired_resolutions or config.max_desired_resolutions == -1:  # noqa: SIM102
                if greater_than(current_values, selected_values):
                    selected_values = current_values
                    selected = current_movie

        return selected

    return None


def move_to_final_location(command: Command, new_metadata: LookedUpFileInfo) -> Command:
    """
    Moves a file or directory to its final location after verifying there is no collision.
    Should a collision occur, the file is appropriately renamed to avoid collision.
    """

    # determine where we will move the movie, and how we will name it.
    # if in_place is False we will move it to the config defined destination dir.
    # if a directory name was passed in we will rename the dir with the relative_path_name from the config
    # else we will just rename the movie in its current location (as all that was defined in the command was the movie file.)
    name_template = get_inplace_name_template_by_type(command.config, new_metadata.type)

    target_dir = command.target_movie_file.parent
    if command.target_directory:
        name_template = get_new_relative_path_name_template_by_type(command.config, new_metadata.type)
        target_dir = command.target_directory.parent

    if not command.inplace:
        name_template = get_new_relative_path_name_template_by_type(command.config, new_metadata.type)
        target_dir = command.config.dest_dir

    infix = 0
    # Find non-conflicting movie name.
    movies: List[str] = []
    while True:
        relative_path = Path(new_metadata.new_file_name(name_template, command.config, f'({infix})'))
        movie_name = target_dir / relative_path
        movie_name = movie_name.resolve()
        infix += 1
        if not movie_name.exists():
            break

        movies.append(str(movie_name))
        if command.target_movie_file.samefile(movie_name):
            break

    # Create the new dir if needed and move the movie file to it.
    movie_name.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(command.target_movie_file, movie_name)
    movies.append(str(movie_name))

    # Now that all files are in place we'll see if we intend to minimize duplicates
    if not command.config.preserve_duplicates and movies:
        # Now set to the final name location since -- will grab the metadata requested
        # incase it has been updated.
        relative_path = Path(new_metadata.new_file_name(name_template, command.config, '(0)'))

        # no move best match to primary movie location.
        final_location = (target_dir / relative_path).resolve()
        selected_movie = selected_best_movie(movies, command.config)
        if selected_movie:
            movies.remove(str(selected_movie))
            if str(selected_movie.resolve()) != str(final_location.resolve()):
                movies.remove(str(final_location))
                final_location.unlink()
                shutil.move(selected_movie, final_location)
                movie_name = final_location

            for movie in movies:
                Path(movie).unlink()

    containing_dir: Optional[Path] = None
    if relative_path.parts:
        containing_dir = target_dir / relative_path.parent

    # we want to retain files if asked and if a directory will exist.
    if command.target_directory and not command.config.del_other_files and containing_dir:
        containing_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f'moving other files to new dir: {containing_dir} from {command.target_directory}')
        # first remove namer log if exists
        possible_log = command.target_movie_file.parent / (command.target_movie_file.stem + '_namer.json.gz')
        if possible_log.exists():
            possible_log.unlink()

        # move directory contents
        for file in command.target_directory.iterdir():
            if file != command.target_movie_file:
                dest_file = containing_dir / file.name
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(file, dest_file)

    if command.target_directory and containing_dir:
        set_permissions(containing_dir, command.config)
    else:
        set_permissions(movie_name, command.config)

    output = Command()
    if movie_name:
        output.target_movie_file = movie_name
        output.input_file = movie_name

    if containing_dir:
        output.target_directory = containing_dir
        output.input_file = containing_dir

    if command.target_directory and not is_relative_to(output.target_directory, command.target_directory):
        shutil.rmtree(command.target_directory)

    return output


def is_relative_to(potential_sub: Optional[Path], potential_parent: Optional[Path]) -> bool:
    try:
        if potential_sub and potential_parent:
            potential_sub.resolve().relative_to(potential_parent.resolve())
            return True
        return False
    except ValueError:
        return False


def is_interesting_movie(path: Optional[Path], config: NamerConfig) -> bool:
    if not path:
        return False

    exists = path.exists()
    suffix = path.suffix.lower()[1:] in config.target_extensions
    size = path.stat().st_size / (1024 * 1024) >= config.min_file_size if path.is_file() else False

    return exists and size and suffix


def gather_target_files_from_dir(dir_to_scan: Path, config: NamerConfig) -> Iterable[Command]:
    """
    Find files to process in a target directory.
    """
    if dir_to_scan and dir_to_scan.is_dir() and dir_to_scan.exists():
        logger.info('Scanning dir {} for sub-dirs/files to process', dir_to_scan)
        mapped: Iterable = map(lambda file: make_command((dir_to_scan / file), config), dir_to_scan.iterdir())
        filtered: Iterable[Command] = filter(lambda file: file is not None, mapped)  # type: ignore
        return filtered

    return []


def __exact_command(target_movie_file: Path, target_dir: Optional[Path], config: NamerConfig) -> Command:
    """
    Given a target movie file and a target containing directory, parse appropriate names as determined by
    config, aka, "prefer_dir_name_if_available".
    """
    command = Command()
    command.target_directory = target_dir
    command.target_movie_file = target_movie_file
    command.parsed_dir_name = bool(target_dir and config.prefer_dir_name_if_available)
    command.config = config
    name = target_movie_file.name

    parsed_dir_name = False
    if target_dir and config.prefer_dir_name_if_available:
        name = target_dir.name + target_movie_file.suffix
        parsed_dir_name = True

    command.parsed_file = parse_file_name(name, config)
    command.parsed_dir_name = parsed_dir_name

    return command


def find_target_file(root_dir: Path, config: NamerConfig) -> Optional[Path]:
    """
    returns largest matching file
    """
    list_of_files = list(root_dir.rglob('**/*.*'))
    file = None
    if list_of_files:
        for target_ext in config.target_extensions:
            filtered = list(filter(lambda o, ext=target_ext: o.suffix and o.suffix.lower()[1:] == ext, list_of_files))
            if not file and filtered:
                file = max(filtered, key=lambda x: x.stat().st_size)

    return file


def make_command(input_file: Path, config: NamerConfig, nfo: bool = False, inplace: bool = False, uuid: Optional[str] = None, ignore_file_restrictions: bool = False, is_auto: bool = True) -> Optional[Command]:
    """
    Create a Command describing how an input path (file or directory) should be processed.
    
    If input_file is a directory, the function locates the best candidate movie file inside it; otherwise the input_file itself is used as the target movie. If no suitable movie is found or the target is filtered out by file-extension/size rules (unless ignore_file_restrictions is True), returns None.
    
    Parameters:
        input_file: Path to a file or directory to build a Command for.
        config: NamerConfig used to find target files and apply filtering rules.
        nfo: When True, indicates the command should prefer metadata from accompanying .nfo files.
        inplace: When True, the command will operate in place rather than moving files to a new location.
        uuid: Optional TPDB or external identifier to attach to the resulting Command.
        ignore_file_restrictions: If True, bypasses extension/size filtering and accepts any found target movie.
        is_auto: Marks whether the generated Command originated automatically (True) or was user-initiated (False).
    
    Returns:
        A populated Command when a target movie is found and accepted; otherwise None.
    """
    target_dir = input_file if input_file.is_dir() else None
    target_movie = input_file if not input_file.is_dir() else find_target_file(input_file, config)
    if not target_movie:
        return None

    # Early filter: if file is not interesting (wrong extension/too small), do not parse
    if not ignore_file_restrictions and not is_interesting_movie(target_movie, config):
        return None

    target_file = __exact_command(target_movie, target_dir, config)
    target_file.input_file = input_file
    target_file.tpdb_id = uuid
    target_file.write_from_nfos = nfo
    target_file.inplace = inplace
    target_file.is_auto = is_auto

    return target_file


def make_command_relative_to(input_dir: Path, relative_to: Path, config: NamerConfig, nfo: bool = False, inplace: bool = False, uuid: Optional[str] = None, is_auto: bool = True) -> Optional[Command]:
    """
    Create a Command for a directory using its path relative to another directory.
    
    If input_dir is inside relative_to, compute the relative path, select the first path component under relative_to
    (as the primary target file or directory) and call make_command on that target. Returns None if input_dir is not
    relative to relative_to or no relative path can be computed.
    
    Parameters:
        input_dir (Path): Directory to be interpreted relative to `relative_to`.
        relative_to (Path): Base directory to which `input_dir` should be relative.
        nfo (bool): If True, prefer metadata from accompanying `.nfo` files when building the Command.
        inplace (bool): If True, produce a Command configured to operate in-place.
        uuid (Optional[str]): Optional identifier to attach to the created Command.
        is_auto (bool): Whether the created Command should be marked as automatically generated.
    
    Returns:
        Optional[Command]: A newly created Command for the corresponding target under `relative_to`, or None.
    """
    if is_relative_to(input_dir, relative_to):
        relative_path = input_dir.resolve().relative_to(relative_to.resolve())
        if relative_path:
            target_file = relative_to / relative_path.parts[0]
            return make_command(target_file, config, nfo, inplace, uuid, is_auto=is_auto)

    return None


def get_inplace_name_template_by_type(config: NamerConfig, scene_type: Optional[SceneType] = None):
    name_template = None
    if scene_type:
        if scene_type == SceneType.SCENE:
            name_template = config.inplace_name_scene
        elif scene_type == SceneType.MOVIE:
            name_template = config.inplace_name_movie
        elif scene_type == SceneType.JAV:
            name_template = config.inplace_name_jav

    if not name_template:
        name_template = config.inplace_name

    return name_template


def get_new_relative_path_name_template_by_type(config: NamerConfig, scene_type: Optional[SceneType] = None):
    name_template = None
    if scene_type:
        if scene_type == SceneType.SCENE:
            name_template = config.new_relative_path_name_scene
        elif scene_type == SceneType.MOVIE:
            name_template = config.new_relative_path_name_movie
        elif scene_type == SceneType.JAV:
            name_template = config.new_relative_path_name_jav

    if not name_template:
        name_template = config.new_relative_path_name

    return name_template


def main(arg_list: List[str]):
    """
    Attempt to parse a name.
    """
    description = 'You are using the file name parser of the Namer project. Expects a single input, and will output the contents of FileInfo, which is the internal input to the namer_metadatapi.py script. Output will be the representation of that FileInfo.\n'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f', '--file', help='String to parse for name parts', required=True)
    parser.add_argument('-c', '--configfile', help='override location for a configuration file.', type=Path)
    args = parser.parse_args(arg_list)
    target = Path(args.file).resolve()
    config_file = Path(args.configfile).resolve()
    target_file = make_command(target, default_config(config_file))
    if target_file:
        print(target_file.parsed_file)


if __name__ == '__main__':
    main(arg_list=sys.argv[1:])
