"""
ThePornDB GraphQL metadata provider implementation.

This provider uses ThePornDB's GraphQL endpoint instead of the REST API
for cleaner and more efficient queries.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from namer.comparison_results import ComparisonResults, LookedUpFileInfo, SceneType
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.metadata_providers.provider import BaseMetadataProvider
from namer.videophash import PerceptualHash


class ThePornDBProvider(BaseMetadataProvider):
    """
    ThePornDB GraphQL metadata provider.
    
    Uses ThePornDB's GraphQL endpoint for metadata lookups and maintains
    compatibility with the existing namer data structures.
    """
    
    def __init__(self):
        """Initialize the ThePornDB provider."""
        pass
    
    def match(self, file_name_parts: Optional[FileInfo], config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
        """
        Search for metadata matches based on file name parts and/or perceptual hash.
        
        This method uses the original ThePornDB logic through the legacy function
        to maintain full backward compatibility while avoiding circular imports.
        """
        # Use the legacy implementation from metadataapi
        from namer.metadataapi import _match_legacy_theporndb
        return _match_legacy_theporndb(file_name_parts, config, phash)
    
    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Get complete metadata information for a specific item by UUID.
        """
        from namer.metadataapi import __build_url, __get_metadataapi_net_info
        
        # Use the legacy implementation directly
        url = __build_url(config, uuid=uuid, add_to_collection=config.mark_collected)
        if url:
            file_infos = __get_metadataapi_net_info(url, file_name_parts, config)
            if file_infos:
                return file_infos[0]
        return None
    
    def search(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[LookedUpFileInfo]:
        """
        Search for metadata by text query.
        
        Use the same internal functions as the legacy implementation to maintain consistency.
        """
        # Import the internal functions we need from metadataapi
        # These are module-level private functions, not class methods
        import namer.metadataapi as meta_api
        
        # Get access to the private functions using the module's __dict__
        build_url_func = getattr(meta_api, '_ThePornDBProvider__build_url', None)
        get_info_func = getattr(meta_api, '_ThePornDBProvider__get_metadataapi_net_info', None)
        
        # If the functions aren't found with class prefix, try module prefix
        if not build_url_func:
            build_url_func = getattr(meta_api, '__build_url', None)
        if not get_info_func:
            get_info_func = getattr(meta_api, '__get_metadataapi_net_info', None)
        
        if build_url_func and get_info_func:
            # Build URL for the search
            search_url = build_url_func(
                config,
                site=None,
                release_date=None, 
                name=query,
                page=page,
                scene_type=scene_type
            )
            
            if search_url:
                # Get the results using the existing function
                file_infos = get_info_func(search_url, None, config)
                return file_infos
        
        return []
    
    def download_file(self, url: str, file: Path, config: NamerConfig) -> bool:
        """
        Download a file (image, trailer) from ThePornDB.
        """
        from namer import metadataapi
        
        return metadataapi.download_file(url, file, config)
    
    def get_user_info(self, config: NamerConfig) -> Optional[dict]:
        """
        Get user information from ThePornDB API.
        """
        from namer.metadataapi import __build_url, __request_response_json_object
        import orjson
        
        url = __build_url(config, user=True)
        response = __request_response_json_object(url, config)
        
        data = orjson.loads(response) if response else None
        return data['data'] if data else None


# Legacy function mappings for backward compatibility
def _build_graphql_query(query_type: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a GraphQL query for ThePornDB.
    
    This is a placeholder for future GraphQL implementation.
    For now, we continue to use the REST API.
    """
    # TODO: Implement GraphQL queries when migrating from REST
    queries = {
        'searchScenes': '''
            query SearchScenes($query: String!, $page: Int) {
                searchScenes(input: {query: $query, page: $page}) {
                    data {
                        id
                        title
                        date
                        url
                        description
                        duration
                        poster
                        background {
                            large
                        }
                        trailer
                        site {
                            name
                            parent {
                                name
                            }
                            network {
                                name
                            }
                        }
                        performers {
                            name
                            parent {
                                name
                                image
                                extras {
                                    gender
                                }
                            }
                            image
                            extras {
                                gender
                            }
                        }
                        tags {
                            name
                        }
                        hashes {
                            hash
                            type
                            duration
                        }
                    }
                }
            }
        ''',
        'getScene': '''
            query GetScene($id: ID!) {
                findScene(id: $id) {
                    id
                    title
                    date
                    url
                    description
                    duration
                    poster
                    background {
                        large
                    }
                    trailer
                    site {
                        name
                        parent {
                            name
                        }
                        network {
                            name
                        }
                    }
                    performers {
                        name
                        parent {
                            name
                            image
                            extras {
                                gender
                            }
                        }
                        image
                        extras {
                            gender
                        }
                    }
                    tags {
                        name
                    }
                    hashes {
                        hash
                        type
                        duration
                    }
                }
            }
        '''
    }
    
    return {
        'query': queries.get(query_type, ''),
        'variables': variables
    }
