"""
ThePornDB GraphQL metadata provider implementation.

This provider uses ThePornDB's GraphQL endpoint.
"""

import os
import orjson
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from namer.comparison_results import ComparisonResults, LookedUpFileInfo, SceneType, HashType, Performer, SceneHash
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.http import Http, RequestType
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

    @logger.catch
    def _graphql_request(self, query: str, variables: Dict[str, Any], config: NamerConfig) -> Optional[Dict[str, Any]]:
        """
        Send a GraphQL request to ThePornDB.

        Args:
            query: GraphQL query string
            variables: Query variables
            config: Namer configuration

        Returns:
            GraphQL response data or None if request failed
        """
        headers = {
            'Authorization': f'Bearer {config.porndb_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'namer-1',
        }

        payload = {'query': query, 'variables': variables}

        data = orjson.dumps(payload)
        # Endpoint resolution order: env > config override > built-in default
        base = os.environ.get('TPDB_ENDPOINT') or (config.override_tpdb_address or '').strip() or 'https://theporndb.net'
        graphql_url = base.rstrip('/') + '/graphql'

        try:
            http = Http.request(RequestType.POST, graphql_url, cache_session=config.cache_session, headers=headers, data=data)

            if http.ok:
                response_data = orjson.loads(http.content)

                # Check for GraphQL errors
                if 'errors' in response_data:
                    for error in response_data['errors']:
                        logger.error(f'GraphQL error: {error.get("message", "Unknown error")}')
                    return None

                return response_data.get('data')
            else:
                logger.error(f'HTTP error {http.status_code}: {http.text}')
                return None

        except Exception as e:
            logger.error(f'GraphQL request failed: {e}')
            return None

    def _graphql_scene_to_fileinfo(self, scene_data: Dict[str, Any], original_query: str, original_response: str, name_parts: Optional[FileInfo]) -> LookedUpFileInfo:
        """
        Convert GraphQL scene data to LookedUpFileInfo object.

        Args:
            scene_data: Scene data from GraphQL response
            original_query: Original query for reference
            original_response: Original response for reference
            name_parts: Parsed filename parts

        Returns:
            LookedUpFileInfo object
        """
        file_info = LookedUpFileInfo()

        # Basic scene information
        file_info.type = SceneType.SCENE  # GraphQL response should indicate type

        # Use numeric _id for UUID to maintain legacy compatibility
        numeric_id = scene_data.get('_id', scene_data.get('id', ''))
        file_info.uuid = f'scenes/{numeric_id}'
        file_info.guid = scene_data.get('id', '')  # Keep GUID as the full UUID
        file_info.name = scene_data.get('title', '')
        file_info.description = scene_data.get('description', '')
        file_info.date = scene_data.get('date', '')
        # Handle both old 'url' field and new 'urls' structure
        if 'urls' in scene_data and scene_data['urls']:
            file_info.source_url = scene_data['urls'].get('view', '')
        else:
            file_info.source_url = scene_data.get('url', '')
        file_info.duration = scene_data.get('duration')

        # External ID
        if 'external_id' in scene_data:
            file_info.external_id = scene_data['external_id']

        # Image URLs
        if 'poster' in scene_data:
            file_info.poster_url = scene_data['poster']

        if 'background' in scene_data and scene_data['background']:
            if isinstance(scene_data['background'], dict):
                file_info.background_url = scene_data['background'].get('large', '')
            else:
                file_info.background_url = scene_data['background']

        if 'trailer' in scene_data:
            file_info.trailer_url = scene_data['trailer']

        # Site information
        if 'site' in scene_data and scene_data['site']:
            site = scene_data['site']
            file_info.site = site.get('name', '')

            # Parent and network information
            if 'parent' in site and site['parent']:
                file_info.parent = site['parent'].get('name', '')

            if 'network' in site and site['network']:
                file_info.network = site['network'].get('name', '')

        # Performers
        if 'performers' in scene_data:
            for perf_data in scene_data['performers']:
                performer_name = perf_data.get('name', '')
                if not performer_name:
                    continue

                # Use parent name if available
                if 'parent' in perf_data and perf_data['parent'] and 'name' in perf_data['parent']:
                    performer_name = perf_data['parent']['name']

                performer = Performer(performer_name)
                performer.alias = perf_data.get('name', '')

                # Gender information
                if 'parent' in perf_data and perf_data['parent'] and 'extras' in perf_data['parent']:
                    performer.role = perf_data['parent']['extras'].get('gender', '')
                elif 'extras' in perf_data:
                    performer.role = perf_data['extras'].get('gender', '')

                # Image information
                if 'parent' in perf_data and perf_data['parent'] and 'image' in perf_data['parent']:
                    performer.image = perf_data['parent']['image']
                elif 'image' in perf_data:
                    performer.image = perf_data['image']

                file_info.performers.append(performer)

        # Tags (deduplicated and sorted to match legacy behavior)
        if 'tags' in scene_data:
            tag_names = [tag['name'] for tag in scene_data['tags'] if 'name' in tag]
            # Deduplicate first, then sort to ensure consistent ordering
            file_info.tags = sorted(list(dict.fromkeys(tag_names)))

        # Hashes
        if 'hashes' in scene_data:
            for hash_data in scene_data['hashes']:
                hash_type = HashType.PHASH  # Default, should map from hash_data['type']
                if 'type' in hash_data:
                    try:
                        hash_type = HashType[hash_data['type'].upper()]
                    except KeyError:
                        hash_type = HashType.PHASH

                scene_hash = SceneHash(hash_data.get('hash', ''), hash_type, hash_data.get('duration'))
                file_info.hashes.append(scene_hash)

        # Set original query/response for compatibility
        file_info.original_query = original_query
        file_info.original_response = original_response
        file_info.original_parsed_filename = name_parts

        # Compatibility fields
        file_info.look_up_site_id = str(numeric_id)

        return file_info

    def match(self, file_name_parts: Optional[FileInfo], config: NamerConfig, phash: Optional[PerceptualHash] = None) -> ComparisonResults:
        """
        Search for metadata matches based on file name parts and/or perceptual hash using GraphQL.
        """
        results = []

        if not file_name_parts and not phash:
            return ComparisonResults(results, file_name_parts)

        # Build search query based on available information
        search_terms = []

        if file_name_parts:
            if file_name_parts.site:
                search_terms.append(file_name_parts.site)
            if file_name_parts.name:
                search_terms.append(file_name_parts.name)
            if file_name_parts.date:
                search_terms.append(file_name_parts.date)

        # If we have a perceptual hash, try hash search first (temporarily disabled until schema confirmed)
        if phash:
            hash_results = self._search_by_hash(phash, config)
            for scene_data in hash_results:
                file_info = self._graphql_scene_to_fileinfo(scene_data, f'hash:{phash.phash}', orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'), file_name_parts)
                # Mark as found via phash for scoring
                file_info._found_via_phash = True
                results.append(file_info)

        # Text-based search
        if search_terms:
            query_string = ' '.join(search_terms)
            text_results = self._search_scenes(query_string, SceneType.SCENE, config)

            for scene_data in text_results:
                # Skip if already found via hash
                scene_id = scene_data.get('id', '')
                if any(r.guid == scene_id for r in results):
                    continue

                file_info = self._graphql_scene_to_fileinfo(scene_data, query_string, orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'), file_name_parts)
                results.append(file_info)

        # Convert to ComparisonResult objects and evaluate matches
        # Import the internal functions we need from metadataapi
        import namer.metadataapi as meta_api

        # Use getattr to access private functions without name mangling issues
        evaluate_match_func = getattr(meta_api, '_ThePornDBProvider__evaluate_match', None)
        match_weight_func = getattr(meta_api, '_ThePornDBProvider__match_weight', None)

        # If the functions aren't found with class prefix, try module prefix
        if not evaluate_match_func:
            evaluate_match_func = getattr(meta_api, '__evaluate_match', None)
        if not match_weight_func:
            match_weight_func = getattr(meta_api, '__match_weight', None)

        comparison_results = []

        if evaluate_match_func:
            for file_info in results:
                comparison_result = evaluate_match_func(file_name_parts, file_info, config, phash)
                comparison_results.append(comparison_result)

        # Sort by match quality
        if match_weight_func:
            comparison_results = sorted(comparison_results, key=match_weight_func, reverse=True)

        return ComparisonResults(comparison_results, file_name_parts)

    def _search_scenes(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[Dict[str, Any]]:
        """
        Search for scenes using GraphQL.
        Primary: searchScenes(input: {query, page}) to match test server.
        Fallback: searchScene(term: $term) for newer schema compatibility.

        Args:
            query: Search query string
            scene_type: Type of scene to search for
            config: Namer configuration
            page: Page number for pagination

        Returns:
            List of scene data from GraphQL response
        """
        # Try current schema: searchScene(term: $term) - this is the correct API
        search_scene_query = """
            query SearchScene($term: String!) {
                searchScene(term: $term) {
                    id
                    title
                    date
                    description
                    duration
                    url
                    urls { view }
                    site { name parent { name } network { name } }
                    performers {
                        name
                        parent { name image extras { gender } }
                        image
                        extras { gender }
                    }
                    tags { name }
                    hashes { hash type duration }
                }
            }
        """
        variables = {'term': query}
        response_data = self._graphql_request(search_scene_query, variables, config)
        if response_data and 'searchScene' in response_data:
            scenes = response_data['searchScene']
            return scenes if isinstance(scenes, list) else []

        return []

    def _search_by_hash(self, phash: PerceptualHash, config: NamerConfig) -> List[Dict[str, Any]]:
        """
        Search for scenes by perceptual hash using GraphQL.

        Args:
            phash: Perceptual hash to search for
            config: Namer configuration

        Returns:
            List of scene data from GraphQL response
        """
        # The current public TPDB GraphQL schema does not expose a hash search.
        # Disable GraphQL hash search for now; hash-based matching will be covered by name search and/or future schema support.
        return []

    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Get complete metadata information for a specific item by UUID using GraphQL.
        """
        # Extract scene ID from UUID (format: scenes/12345)
        scene_id = uuid
        if '/' in uuid:
            scene_id = uuid.split('/')[-1]

        scene_query = """
            query GetScene($id: ID!) {
                findScene(id: $id) {
                    id
                    title
                    date
                    description
                    duration
                    url
                    urls {
                        view
                    }
                    isCollected
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
        """

        variables = {'id': scene_id}

        response_data = self._graphql_request(scene_query, variables, config)

        if response_data and 'findScene' in response_data and response_data['findScene']:
            scene_data = response_data['findScene']

            # Mark as collected if needed
            if config.mark_collected and 'isCollected' in scene_data and not scene_data['isCollected']:
                self._mark_collected(scene_id, config)

            file_info = self._graphql_scene_to_fileinfo(scene_data, f'findScene:{scene_id}', orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'), file_name_parts)

            # Set collection status
            file_info.is_collected = scene_data.get('isCollected', False)

            return file_info

        return None

    def _mark_collected(self, scene_id: str, config: NamerConfig) -> bool:
        """
        Mark a scene as collected using GraphQL mutation.

        Args:
            scene_id: Scene ID to mark as collected
            config: Namer configuration

        Returns:
            True if successful, False otherwise
        """
        mutation = """
            mutation MarkCollected($sceneId: ID!) {
                markSceneCollected(sceneId: $sceneId) {
                    success
                    message
                }
            }
        """

        variables = {'sceneId': scene_id}

        response_data = self._graphql_request(mutation, variables, config)

        if response_data and 'markSceneCollected' in response_data:
            result = response_data['markSceneCollected']
            return result.get('success', False)

        return False

    def _share_hash(self, scene_id: str, scene_hash: SceneHash, config: NamerConfig) -> bool:
        """
        Share a perceptual hash for a scene using GraphQL mutation.

        Args:
            scene_id: Scene ID to share hash for
            scene_hash: Hash data to share
            config: Namer configuration

        Returns:
            True if successful, False otherwise
        """
        mutation = """
            mutation ShareHash($sceneId: ID!, $hash: String!, $hashType: String!, $duration: Int) {
                shareSceneHash(input: {
                    sceneId: $sceneId,
                    hash: $hash,
                    hashType: $hashType,
                    duration: $duration
                }) {
                    success
                    message
                }
            }
        """

        variables = {'sceneId': scene_id, 'hash': scene_hash.hash, 'hashType': scene_hash.type.value, 'duration': scene_hash.duration}

        logger.info(f'Sending {scene_hash.type.value}: {scene_hash.hash} with duration {scene_hash.duration}')

        response_data = self._graphql_request(mutation, variables, config)

        if response_data and 'shareSceneHash' in response_data:
            result = response_data['shareSceneHash']
            return result.get('success', False)

        return False

    def search(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[LookedUpFileInfo]:
        """
        Search for metadata by text query using GraphQL.
        """
        scenes = self._search_scenes(query, scene_type, config, page)
        file_infos: List[LookedUpFileInfo] = []
        for scene_data in scenes:
            file_info = self._graphql_scene_to_fileinfo(
                scene_data,
                query,
                orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'),
                None,
            )
            file_infos.append(file_info)
        return file_infos

    def download_file(self, url: str, file: Path, config: NamerConfig) -> bool:
        """
        Download a file (image, trailer) from ThePornDB.
        """
        from namer import metadataapi

        return metadataapi.download_file(url, file, config)

    def get_user_info(self, config: NamerConfig) -> Optional[dict]:
        """
        Get user information from ThePornDB using GraphQL.
        """
        user_query = """
            query GetUser {
                me {
                    id
                    name
                }
            }
        """

        response_data = self._graphql_request(user_query, {}, config)

        if response_data and 'me' in response_data:
            return response_data['me']

        return None


# Legacy function mappings for backward compatibility
def _build_graphql_query(query_type: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a GraphQL query for ThePornDB.

    This is a placeholder for future GraphQL implementation.
    For now, we continue to use the REST API.
    """
    # TODO: Implement GraphQL queries when migrating from REST
    queries = {
        'searchScene': """
            query SearchScene($term: String!) {
                searchScene(term: $term) {
                    id
                    title
                    date
                    duration
                    urls { view }
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
        """,
        'getScene': """
            query GetScene($id: ID!) {
                findScene(id: $id) {
                    id
                    title
                    date
                    duration
                    urls { view }
                    isCollected
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
        """,
    }

    return {'query': queries.get(query_type, ''), 'variables': variables}
