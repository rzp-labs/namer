from pathlib import Path

from namer.command import make_command
from namer.namer import process_file
from namer.comparison_results import ComparisonResults, ComparisonResult, LookedUpFileInfo
from namer.fileinfo import FileInfo
from namer.configuration_utils import default_config


def test_flagged_wiring_routes_ambiguous(tmp_path, monkeypatch):
    # Arrange: temp media and ambiguous directory
    src = tmp_path / "src"
    src.mkdir()
    video = src / "video.mp4"
    video.write_bytes(b"x")  # tiny file; we'll bypass size restrictions when creating command

    ambiguous_dir = tmp_path / "ambiguous"
    ambiguous_dir.mkdir()

    # Base config with feature flag enabled and permissive size
    config = default_config(None)
    config.enable_disambiguation = True
    config.ambiguous_dir = ambiguous_dir
    config.min_file_size = 0  # allow tiny test file
    config.search_phash = False  # don't compute phash during test

    # Fake match() to return an ambiguous set where best guid != majority guid
    def fake_match(name_parts, conf, phash=None):
        def mk(guid: str, dist: int) -> ComparisonResult:
            info = LookedUpFileInfo()
            info.guid = guid
            return ComparisonResult(
                name="n",
                name_match=95.0,
                site_match=True,
                date_match=True,
                name_parts=FileInfo(),
                looked_up=info,
                phash_distance=dist,
                phash_duration=True,
            )

        results = [mk("A", 5), mk("B", 6), mk("B", 6), mk("B", 6)]
        return ComparisonResults(results, None)

    monkeypatch.setattr("namer.metadataapi.match", fake_match)

    # Act: build command ignoring file restrictions and process
    cmd = make_command(video, config, ignore_file_restrictions=True)
    out = process_file(cmd)

    # Assert: file was routed to ambiguous_dir under the feature flag
    assert out is not None
    assert out.target_movie_file.parent == ambiguous_dir
