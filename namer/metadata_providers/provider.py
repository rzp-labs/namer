"""
Abstract base class and protocol for metadata providers.

This module defines the interface that all metadata providers must implement
to ensure consistent API across different provider implementations (ThePornDB, StashDB, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Protocol

from namer.comparison_results import ComparisonResults, LookedUpFileInfo, SceneType
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.videophash import PerceptualHash


class MetadataProvider(Protocol):
    """
    Protocol defining the interface for metadata providers.
    
    All metadata providers must implement these methods to provide
    consistent functionality across different provider implementations.
    """
    
    def match(self, file_name_parts: Optional[FileInfo], config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
        """
        Search for metadata matches based on file name parts and/or perceptual hash.
        
        Args:
            file_name_parts: Parsed file name components
            config: Namer configuration
            phash: Optional perceptual hash for matching
            
        Returns:
            ComparisonResults containing sorted list of potential matches
        """
        ...
    
    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Get complete metadata information for a specific item by UUID.
        
        Args:
            file_name_parts: Parsed file name components  
            uuid: Unique identifier for the metadata item
            config: Namer configuration
            
        Returns:
            Complete LookedUpFileInfo or None if not found
        """
        ...
    
    def search(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[LookedUpFileInfo]:
        """
        Search for metadata by text query.
        
        Args:
            query: Search query string
            scene_type: Type of content to search for (SCENE, MOVIE, JAV)  
            config: Namer configuration
            page: Page number for paginated results
            
        Returns:
            List of LookedUpFileInfo results
        """
        ...
    
    def download_file(self, url: str, file: Path, config: NamerConfig) -> bool:
        """
        Download a file (image, trailer) from the provider.
        
        Args:
            url: URL to download
            file: Local file path to save to
            config: Namer configuration
            
        Returns:
            True if successful, False otherwise
        """
        ...
    
    def get_user_info(self, config: NamerConfig) -> Optional[dict]:
        """
        Get user information from the provider API.
        
        Args:
            config: Namer configuration
            
        Returns:
            User info dict or None if not available
        """
        ...


class BaseMetadataProvider(ABC):
    """
    Abstract base class providing common functionality for metadata providers.
    
    Providers can extend this class to inherit common functionality and
    only need to implement the abstract methods specific to their API.
    """
    
    @abstractmethod
    def match(self, file_name_parts: Optional[FileInfo], config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
        """Search for metadata matches."""
        pass
    
    @abstractmethod  
    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """Get complete metadata information for a specific item."""
        pass
    
    @abstractmethod
    def search(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[LookedUpFileInfo]:
        """Search for metadata by text query.""" 
        pass
    
    def download_file(self, url: str, file: Path, config: NamerConfig) -> bool:
        """
        Default file download implementation.
        
        Providers can override this for custom download logic.
        """
        from namer.metadataapi import download_file as default_download
        return default_download(url, file, config)
    
    def get_user_info(self, config: NamerConfig) -> Optional[dict]:
        """
        Default user info implementation.
        
        Returns None by default; providers can override for custom user info.
        """
        return None
