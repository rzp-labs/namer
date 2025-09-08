"""
Metadata providers package.

This package contains implementations of metadata providers for different
adult content databases (ThePornDB, StashDB, etc.).
"""

from .provider import MetadataProvider, BaseMetadataProvider
from .factory import ProviderFactory, get_metadata_provider
from .theporndb_provider import ThePornDBProvider
from .stashdb_provider import StashDBProvider

__all__ = [
    'MetadataProvider', 
    'BaseMetadataProvider',
    'ProviderFactory', 
    'get_metadata_provider',
    'ThePornDBProvider',
    'StashDBProvider'
]
