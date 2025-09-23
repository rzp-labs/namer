from namer.command import make_command
from namer.namer import process_file
from test.utils import (
    create_dummy_video,
    setup_disambiguation_config,
    patch_default_ambiguous_match,
)


def test_flagged_wiring_routes_ambiguous(tmp_path, monkeypatch):
    # Arrange
    video = create_dummy_video(tmp_path)
    config, ambiguous_dir = setup_disambiguation_config(tmp_path, enable_flag=True)
    patch_default_ambiguous_match(monkeypatch)

    # Act: build command ignoring file restrictions and process
    cmd = make_command(video, config, ignore_file_restrictions=True)
    out = process_file(cmd)

    # Assert: file was routed to ambiguous_dir under the feature flag
    assert out is not None
    assert out.target_movie_file.parent == ambiguous_dir
