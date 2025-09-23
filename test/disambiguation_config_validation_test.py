from namer.configuration_utils import validate_disambiguation_config
from namer.configuration_utils import default_config


def test_validate_disambiguation_defaults_valid():
    cfg = default_config(None)
    assert validate_disambiguation_config(cfg) is True


def test_invalid_majority_fraction_out_of_range():
    cfg = default_config(None)
    cfg.phash_majority_accept_fraction = 1.5
    assert validate_disambiguation_config(cfg) is False


def test_invalid_accept_distance_not_less_than_ambiguous_min():
    cfg = default_config(None)
    cfg.phash_accept_distance = cfg.phash_ambiguous_min
    assert validate_disambiguation_config(cfg) is False


def test_invalid_ambiguous_min_greater_than_max():
    cfg = default_config(None)
    cfg.phash_ambiguous_min = 10
    cfg.phash_ambiguous_max = 9
    assert validate_disambiguation_config(cfg) is False


def test_negative_distance_margin_accept():
    cfg = default_config(None)
    cfg.phash_distance_margin_accept = -1
    assert validate_disambiguation_config(cfg) is False
