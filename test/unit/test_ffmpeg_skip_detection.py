"""
Unit tests for FFmpeg skip validation detection logic.

Tests the helper functions that determine whether FFmpeg validation
should be skipped based on environment variables and process context.
"""

import importlib
import sys


def test_skip_when_env_set_true(monkeypatch):
    """Test that NAMER_SKIP_FFMPEG_VALIDATION=true enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', 'true')
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_skip_when_env_set_1(monkeypatch):
    """Test that NAMER_SKIP_FFMPEG_VALIDATION=1 enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', '1')
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_skip_when_env_set_yes(monkeypatch):
    """Test that NAMER_SKIP_FFMPEG_VALIDATION=yes enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', 'yes')
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_skip_when_env_set_on(monkeypatch):
    """Test that NAMER_SKIP_FFMPEG_VALIDATION=on enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', 'on')
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_no_skip_by_default(monkeypatch):
    """Test that without env var and non-pytest argv, skip is disabled."""
    import namer.configuration as cfg
    
    monkeypatch.delenv('NAMER_SKIP_FFMPEG_VALIDATION', raising=False)
    # Ensure argv does not look like pytest
    monkeypatch.setattr(sys, 'argv', ['python', 'script.py'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is False


def test_no_skip_when_env_false(monkeypatch):
    """Test that NAMER_SKIP_FFMPEG_VALIDATION=false disables skip."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', 'false')
    monkeypatch.setattr(sys, 'argv', ['python', 'script.py'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is False


def test_skip_when_pytest_cli_detected(monkeypatch):
    """Test that pytest CLI invocation enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.delenv('NAMER_SKIP_FFMPEG_VALIDATION', raising=False)
    monkeypatch.setattr(sys, 'argv', ['pytest', '-k', 'something'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_skip_when_py_test_cli_detected(monkeypatch):
    """Test that py.test CLI invocation enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.delenv('NAMER_SKIP_FFMPEG_VALIDATION', raising=False)
    monkeypatch.setattr(sys, 'argv', ['py.test', '-v'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_skip_when_pytest_with_path(monkeypatch):
    """Test that pytest with full path enables skip."""
    import namer.configuration as cfg
    
    monkeypatch.delenv('NAMER_SKIP_FFMPEG_VALIDATION', raising=False)
    monkeypatch.setattr(sys, 'argv', ['/usr/local/bin/pytest', 'test.py'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_env_var_takes_precedence(monkeypatch):
    """Test that env var takes precedence over argv detection."""
    import namer.configuration as cfg
    
    monkeypatch.setenv('NAMER_SKIP_FFMPEG_VALIDATION', 'true')
    monkeypatch.setattr(sys, 'argv', ['python', 'script.py'])
    importlib.reload(cfg)
    assert cfg._ffmpeg_should_skip_validation() is True


def test_env_truthy_helper(monkeypatch):
    """Test the _env_truthy helper function."""
    import namer.configuration as cfg
    
    # Test truthy values
    for value in ['1', 'true', 'yes', 'on', 'True', 'TRUE', 'YES', 'ON']:
        monkeypatch.setenv('TEST_VAR', value)
        importlib.reload(cfg)
        assert cfg._env_truthy('TEST_VAR') is True, f"Failed for value: {value}"
    
    # Test falsy values
    for value in ['0', 'false', 'no', 'off', 'False', 'FALSE', 'NO', 'OFF', 'anything']:
        monkeypatch.setenv('TEST_VAR', value)
        importlib.reload(cfg)
        assert cfg._env_truthy('TEST_VAR') is False, f"Failed for value: {value}"
    
    # Test default
    monkeypatch.delenv('TEST_VAR', raising=False)
    importlib.reload(cfg)
    assert cfg._env_truthy('TEST_VAR') is False
    assert cfg._env_truthy('TEST_VAR', 'true') is True
