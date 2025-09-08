"""
Metadata provider factory.

This factory creates the appropriate metadata provider based on configuration.
"""

from typing import Dict, Type

from namer.configuration import NamerConfig
from namer.metadata_providers.provider import MetadataProvider
from namer.metadata_providers.theporndb_provider import ThePornDBProvider
from namer.metadata_providers.stashdb_provider import StashDBProvider


class ProviderFactory:
    """
    Factory for creating metadata provider instances based on configuration.
    """
    
    # Registry of available providers
    _providers: Dict[str, Type[MetadataProvider]] = {
        'theporndb': ThePornDBProvider,
        'stashdb': StashDBProvider,
    }
    
    @classmethod
    def create_provider(cls, config: NamerConfig) -> MetadataProvider:
        """
        Create a metadata provider instance based on the configuration.
        
        Args:
            config: Namer configuration containing provider selection
            
        Returns:
            MetadataProvider instance
            
        Raises:
            ValueError: If the specified provider is not supported
        """
        provider_name = config.metadata_provider.lower()
        
        if provider_name not in cls._providers:
            supported_providers = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unsupported metadata provider: '{provider_name}'. "
                f"Supported providers: {supported_providers}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class()
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[MetadataProvider]) -> None:
        """
        Register a new metadata provider.
        
        Args:
            name: Provider name (used in configuration)
            provider_class: Provider class that implements MetadataProvider
        """
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())


def get_metadata_provider(config: NamerConfig) -> MetadataProvider:
    """
    Convenience function to get a metadata provider instance.
    
    Args:
        config: Namer configuration
        
    Returns:
        MetadataProvider instance
    """
    return ProviderFactory.create_provider(config)
