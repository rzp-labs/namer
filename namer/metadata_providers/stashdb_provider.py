"""
StashDB GraphQL metadata provider implementation.

This provider interfaces with StashDB's GraphQL API to provide
metadata for adult content, mapping results to namer's data structures.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import orjson
from loguru import logger
from orjson import JSONDecodeError

from namer.comparison_results import ComparisonResult, ComparisonResults, HashType, LookedUpFileInfo, Performer, SceneHash, SceneType
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.http import Http, RequestType
from namer.metadata_providers.provider import BaseMetadataProvider
from namer.videophash import PerceptualHash


class StashDBProvider(BaseMetadataProvider):
    """
    StashDB GraphQL metadata provider.
    
    Interfaces with StashDB's GraphQL endpoint to provide metadata
    and maps results to namer's existing data structures.
    """
    
    def __init__(self):
        """Initialize the StashDB provider."""
        pass
    
    def match(self, file_name_parts: Optional[FileInfo], config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
        """
        Search for metadata matches based on file name parts and/or perceptual hash.
        """
        results: List[ComparisonResult] = []
        
        # For now, implement a basic search using scene title
        if file_name_parts and file_name_parts.name:
            scene_results = self.search(file_name_parts.name, SceneType.SCENE, config)
            
            # Convert to ComparisonResult objects
            for scene_info in scene_results:
                # Create a basic comparison result - this would need more sophisticated
                # matching logic similar to what's in metadataapi.py
                comparison_result = ComparisonResult(
                    name=scene_info.name or '',
                    name_match=self._calculate_name_match(file_name_parts.name, scene_info.name),
                    date_match=self._compare_dates(file_name_parts.date, scene_info.date),
                    site_match=self._compare_sites(file_name_parts.site, scene_info.site),
                    name_parts=file_name_parts,
                    looked_up=scene_info,
                    phash_distance=None,  # TODO: Implement phash matching
                    phash_duration=None,
                )
                results.append(comparison_result)
        
        # Handle phash-based searches
        if phash:
            phash_results = self._search_by_phash(phash, config)
            for scene_info in phash_results:
                comparison_result = ComparisonResult(
                    name=scene_info.name or '',
                    name_match=0.0,  # No name match for phash-only results
                    date_match=False,
                    site_match=False,
                    name_parts=file_name_parts,
                    looked_up=scene_info,
                    phash_distance=0,  # Perfect phash match
                    phash_duration=True,
                )
                results.append(comparison_result)
        
        # Sort results by quality
        results = sorted(results, key=self._calculate_match_weight, reverse=True)
        
        return ComparisonResults(results, file_name_parts)
    
    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Get complete metadata information for a specific item by UUID.
        """
        query = {
            'query': '''
                query FindScene($id: ID!) {
                    findScene(id: $id) {
                        id
                        title
                        date
                        urls {
                            url
                        }
                        details
                        duration
                        images {
                            url
                        }
                        studio {
                            name
                            parent {
                                name
                            }
                        }
                        performers {
                            performer {
                                name
                                aliases
                                images {
                                    url
                                }
                                gender
                            }
                        }
                        tags {
                            name
                        }
                        fingerprints {
                            hash
                            algorithm
                            duration
                        }
                    }
                }
            ''',
            'variables': {
                'id': uuid.split('/')[-1]  # Extract ID from UUID
            }
        }
        
        response = self._execute_graphql_query(query, config)
        if response and 'data' in response and response['data']['findScene']:
            return self._map_stashdb_scene_to_fileinfo(response['data']['findScene'], config)
        
        return None
    
    def search(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[LookedUpFileInfo]:
        """
        Search for metadata by text query.
        """
        # StashDB primarily deals with scenes, so we'll search scenes regardless of scene_type
        # Based on error messages, StashDB expects 'term' parameter and returns direct array
        graphql_query = {
            'query': '''
                query SearchScenes($term: String!) {
                    searchScene(term: $term) {
                        id
                        title
                        date
                        urls {
                            url
                        }
                        details
                        duration
                        images {
                            url
                        }
                        studio {
                            name
                            parent {
                                name
                            }
                        }
                        performers {
                            performer {
                                name
                                aliases
                                images {
                                    url
                                }
                                gender
                            }
                        }
                        tags {
                            name
                        }
                        fingerprints {
                            hash
                            algorithm
                            duration
                        }
                    }
                }
            ''',
            'variables': {
                'term': query
            }
        }
        
        response = self._execute_graphql_query(graphql_query, config)
        results = []
        
        if response and 'data' in response and response['data'] and 'searchScene' in response['data']:
            # StashDB returns scenes directly, not wrapped in a 'scenes' object
            scenes = response['data']['searchScene']
            if isinstance(scenes, list):
                for scene in scenes:
                    file_info = self._map_stashdb_scene_to_fileinfo(scene, config)
                    if file_info:
                        results.append(file_info)
        
        return results
    
    def download_file(self, url: str, file: Path, config: NamerConfig) -> bool:
        """
        Download a file (image, trailer) from StashDB.
        """
        # Use the default implementation from base class
        return super().download_file(url, file, config)
    
    def get_user_info(self, config: NamerConfig) -> Optional[dict]:
        """
        Get user information from StashDB API.
        """
        query = {
            'query': '''
                query Me {
                    me {
                        id
                        name
                        roles
                    }
                }
            ''',
            'variables': {}
        }
        
        response = self._execute_graphql_query(query, config)
        if response and 'data' in response and response['data']['me']:
            return response['data']['me']
        
        return None
    
    def _execute_graphql_query(self, query: Dict[str, Any], config: NamerConfig) -> Optional[Dict[str, Any]]:
        """
        Execute a GraphQL query against StashDB.
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'namer-1',
        }
        
        if config.stashdb_token:
            # Try different authentication methods
            # Method 1: Bearer token (current)
            headers['Authorization'] = f'Bearer {config.stashdb_token}'
            
            # Method 2: API key header (alternative)
            # headers['ApiKey'] = config.stashdb_token
            
            # Method 3: Basic auth (alternative)
            # import base64
            # auth_string = base64.b64encode(f'api:{config.stashdb_token}'.encode()).decode()
            # headers['Authorization'] = f'Basic {auth_string}'
        
        data = orjson.dumps(query)
        http = Http.request(RequestType.POST, config.stashdb_endpoint, cache_session=config.cache_session, headers=headers, data=data)
        
        if http.ok:
            try:
                response_data = orjson.loads(http.content)
                
                # Check for GraphQL errors
                if 'errors' in response_data:
                    logger.error(f'StashDB GraphQL errors: {response_data["errors"]}')
                
                return response_data
            except JSONDecodeError as e:
                logger.error(f'Failed to parse StashDB response: {e}')
        else:
            logger.error(f'StashDB API error: {http.status_code} - {http.text}')
        
        return None
    
    def _map_stashdb_scene_to_fileinfo(self, scene: Dict[str, Any], config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Map StashDB scene data to LookedUpFileInfo.
        """
        file_info = LookedUpFileInfo()
        
        # Basic scene information
        file_info.type = SceneType.SCENE
        file_info.uuid = f"scenes/{scene['id']}"
        file_info.guid = scene['id']
        file_info.name = scene.get('title', '')
        file_info.description = scene.get('details', '')
        file_info.date = scene.get('date', '')
        
        # Handle URLs array (StashDB uses 'urls' not 'url')
        if scene.get('urls') and len(scene['urls']) > 0:
            file_info.source_url = scene['urls'][0].get('url', '')
        
        file_info.duration = scene.get('duration')
        
        # Studio information
        if scene.get('studio'):
            studio = scene['studio']
            file_info.site = studio.get('name', '')
            if studio.get('parent'):
                file_info.parent = studio['parent'].get('name', '')
        
        # Images
        if scene.get('images') and len(scene['images']) > 0:
            file_info.poster_url = scene['images'][0].get('url', '')
        
        # Performers
        if scene.get('performers'):
            for perf_data in scene['performers']:
                performer_info = perf_data.get('performer', {})
                if performer_info.get('name'):
                    performer = Performer(performer_info['name'])
                    performer.role = performer_info.get('gender', '')
                    
                    # Handle aliases
                    if performer_info.get('aliases'):
                        performer.alias = ', '.join(performer_info['aliases'])
                    
                    # Handle images
                    if performer_info.get('images') and len(performer_info['images']) > 0:
                        performer.image = performer_info['images'][0].get('url', '')
                    
                    file_info.performers.append(performer)
        
        # Tags
        if scene.get('tags'):
            file_info.tags = [tag['name'] for tag in scene['tags'] if tag.get('name')]
        
        # Hashes/Fingerprints
        if scene.get('fingerprints'):
            for fingerprint in scene['fingerprints']:
                hash_type = fingerprint.get('algorithm', '').upper()
                if hash_type == 'PHASH':
                    scene_hash = SceneHash(
                        hash=fingerprint.get('hash', ''),
                        type=HashType.PHASH,
                        duration=fingerprint.get('duration')
                    )
                    file_info.hashes.append(scene_hash)
        
        return file_info
    
    def _search_by_phash(self, phash: PerceptualHash, config: NamerConfig) -> List[LookedUpFileInfo]:
        """
        Search for scenes by perceptual hash.
        """
        # Note: This query structure is a guess - StashDB phash search may need different approach
        query = {
            'query': '''
                query SearchByFingerprint($hash: String!) {
                    findSceneByFingerprint(fingerprint: {hash: $hash, algorithm: PHASH}) {
                        id
                        title
                        date
                        urls {
                            url
                        }
                        details
                        duration
                        images {
                            url
                        }
                        studio {
                            name
                            parent {
                                name
                            }
                        }
                        performers {
                            performer {
                                name
                                aliases
                                images {
                                    url
                                }
                                gender
                            }
                        }
                        tags {
                            name
                        }
                        fingerprints {
                            hash
                            algorithm
                            duration
                        }
                    }
                }
            ''',
            'variables': {
                'hash': str(phash.phash)
            }
        }
        
        response = self._execute_graphql_query(query, config)
        results = []
        
        if response and 'data' in response and 'findSceneByFingerprint' in response['data']:
            scene = response['data']['findSceneByFingerprint']
            if scene:  # Single scene result
                file_info = self._map_stashdb_scene_to_fileinfo(scene, config)
                if file_info:
                    results.append(file_info)
        
        return results
    
    def _calculate_name_match(self, query_name: Optional[str], scene_name: Optional[str]) -> float:
        """
        Calculate name match percentage between query and scene names.
        """
        if not query_name or not scene_name:
            return 0.0
        
        # Use rapidfuzz for fuzzy string matching
        import rapidfuzz.fuzz
        return rapidfuzz.fuzz.ratio(query_name.lower(), scene_name.lower())
    
    def _compare_dates(self, query_date: Optional[str], scene_date: Optional[str]) -> bool:
        """
        Compare dates between query and scene.
        """
        if not query_date or not scene_date:
            return False
        return query_date == scene_date
    
    def _compare_sites(self, query_site: Optional[str], scene_site: Optional[str]) -> bool:
        """
        Compare sites between query and scene.
        """
        if not query_site or not scene_site:
            return False
        return query_site.lower() in scene_site.lower()
    
    def _calculate_match_weight(self, result: ComparisonResult) -> float:
        """
        Calculate match weight for sorting results.
        """
        weight = 0.0
        
        # Phash matches get highest priority
        if result.phash_distance is not None:
            weight += max(1000 - result.phash_distance * 125, 0)
            if result.site_match:
                weight += 100
            if result.date_match:
                weight += 100
            if result.name_match:
                weight += result.name_match
        
        # Name matches
        if result.site_match and result.date_match and result.name_match and result.name_match >= 94.9:
            weight += 1000.0
            weight += result.name_match
        
        return weight
