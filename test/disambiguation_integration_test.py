import gzip
import json

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

    # Summary should include ambiguous metadata
    summary_path = ambiguous_dir / f'{out.target_movie_file.stem}_namer_summary.json'
    summary = json.loads(summary_path.read_text())
    assert summary['ambiguous_reason'] == 'phash_decision_ambiguous'
    assert summary['ambiguous_candidates'] == ['A', 'B']

    # Ambiguity note should be created alongside the moved file
    note_path = ambiguous_dir / f'{out.target_movie_file.stem}.ambiguous.json'
    note = json.loads(note_path.read_text())
    assert note['ambiguous_reason'] == 'phash_decision_ambiguous'
    assert note['candidate_guids'] == ['A', 'B']

    # Compressed log should contain the same metadata when decompressed
    log_path = ambiguous_dir / f'{out.target_movie_file.stem}_namer.json.gz'
    with gzip.open(log_path, 'rt', encoding='utf-8') as compressed_log:
        log_data = json.loads(compressed_log.read())
    assert log_data['ambiguous_reason'] == 'phash_decision_ambiguous'
    assert log_data['ambiguous_candidates'] == ['A', 'B']
