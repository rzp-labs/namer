from namer.command import make_command
from namer.namer import process_file
from test.utils import (
    create_dummy_video,
    setup_disambiguation_config,
    patch_default_ambiguous_match,
)


def test_flag_off_does_not_route_ambiguous(tmp_path, monkeypatch):
    # Arrange
    video = create_dummy_video(tmp_path)
    config, ambiguous_dir = setup_disambiguation_config(tmp_path, enable_flag=False)
    patch_default_ambiguous_match(monkeypatch)

    # Act
    cmd = make_command(video, config, ignore_file_restrictions=True)
    out = process_file(cmd)

    # Assert: no routing to ambiguous_dir when flag is off
    assert out is not None
    assert out.target_movie_file.parent != ambiguous_dir
