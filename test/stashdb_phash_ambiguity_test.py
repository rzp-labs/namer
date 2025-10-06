from namer.comparison_results import HashType, LookedUpFileInfo, SceneHash
from namer.metadata_providers.stashdb_provider import StashDBProvider
from namer.videophash import return_perceptual_hash
from test.utils import sample_config


def _make_scene(guid: str) -> LookedUpFileInfo:
    scene = LookedUpFileInfo()
    scene.guid = guid
    scene.uuid = f'scenes/{guid}'
    scene.name = f'Scene {guid[-1]}'
    scene.date = '2024-01-01'
    scene.site = 'Sample Studio'
    scene.hashes.append(SceneHash('ffffffffffffffff', HashType.PHASH, 600))
    return scene


def test_stashdb_phash_multiple_scene_ids_returns_candidates(monkeypatch):
    config = sample_config()
    provider = StashDBProvider()
    phash = return_perceptual_hash(600, 'ffffffffffffffff', 'oshash')

    scenes = [_make_scene('guid-a'), _make_scene('guid-b')]

    def fake_search(self, phash_arg, config_arg):
        assert phash_arg == phash
        assert config_arg is config
        return scenes

    monkeypatch.setattr(StashDBProvider, '_search_by_phash', fake_search)

    results = provider.match(None, config, phash=phash)

    guids = {result.looked_up.guid for result in results.results}
    assert guids == {'guid-a', 'guid-b'}
    assert not results.get_match()
    assert results.ambiguous_reason == 'phash_consensus_not_met'
    assert results.candidate_guids == ['guid-a', 'guid-b']


def test_stashdb_phash_threshold_accepts_majority(monkeypatch):
    config = sample_config()
    config.phash_unique_threshold = 0.5
    provider = StashDBProvider()
    phash = return_perceptual_hash(600, 'ffffffffffffffff', 'oshash')

    scenes = [_make_scene('guid-a'), _make_scene('guid-a'), _make_scene('guid-b')]

    def fake_search(self, phash_arg, config_arg):
        assert phash_arg == phash
        assert config_arg is config
        return scenes

    monkeypatch.setattr(StashDBProvider, '_search_by_phash', fake_search)

    results = provider.match(None, config, phash=phash)

    assert len(results.results) == 1
    match = results.get_match()
    assert match is not None
    assert match.looked_up.guid == 'guid-a'
    assert results.ambiguous_reason is None
    assert results.candidate_guids == []


def test_stashdb_phash_threshold_requires_supermajority(monkeypatch):
    config = sample_config()
    config.phash_unique_threshold = 0.75
    provider = StashDBProvider()
    phash = return_perceptual_hash(600, 'ffffffffffffffff', 'oshash')

    scenes = [_make_scene('guid-a'), _make_scene('guid-a'), _make_scene('guid-b')]

    def fake_search(self, phash_arg, config_arg):
        assert phash_arg == phash
        assert config_arg is config
        return scenes

    monkeypatch.setattr(StashDBProvider, '_search_by_phash', fake_search)

    results = provider.match(None, config, phash=phash)

    guids = {result.looked_up.guid for result in results.results}
    assert guids == {'guid-a', 'guid-b'}
    assert not results.get_match()
    assert results.ambiguous_reason == 'phash_consensus_not_met'
    assert results.candidate_guids == ['guid-a', 'guid-b']


def test_stashdb_phash_results_without_guids_sets_name_candidates(monkeypatch):
    config = sample_config()
    provider = StashDBProvider()
    phash = return_perceptual_hash(600, 'ffffffffffffffff', 'oshash')

    scenes = [_make_scene('guid-a'), _make_scene('guid-b')]
    for scene in scenes:
        scene.guid = None
        scene.uuid = None

    def fake_search(self, phash_arg, config_arg):
        assert phash_arg == phash
        assert config_arg is config
        return scenes

    monkeypatch.setattr(StashDBProvider, '_search_by_phash', fake_search)

    results = provider.match(None, config, phash=phash)

    assert not results.get_match()
    assert results.ambiguous_reason == 'phash_missing_guids'
    assert results.candidate_guids == ['Scene a', 'Scene b']
    