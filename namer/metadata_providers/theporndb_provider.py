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
from namer.videophash import PerceptualHash, imagehash


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
        
        payload = {
            'query': query,
            'variables': variables
        }
        
        data = orjson.dumps(payload)
        # Endpoint resolution order: env > config override > built-in default
        base = os.environ.get('TPDB_ENDPOINT') or (config.override_tpdb_address or '').strip() or 'https://theporndb.net'
        graphql_url = base.rstrip('/') + '/graphql'
        
        try:
            http = Http.request(
                RequestType.POST, 
                graphql_url, 
                cache_session=config.cache_session, 
                headers=headers, 
                data=data
            )
            
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
        Convert a GraphQL scene payload into a LookedUpFileInfo populated for legacy compatibility.
        
        Creates and returns a LookedUpFileInfo with fields mapped from the GraphQL scene object:
        - uuid is derived from `_id` (fallback to `id`) and formatted as `scenes/<numeric_id>`.
        - guid, name (title), description (details), date, duration, and source_url (first entry of `urls`) are copied when present.
        - poster_url, background_url (handles dict with `large` or plain string), and trailer_url are copied when present.
        - site and parent are populated from `studio` → `name` and `studio.parent.name` when available.
        - performers are built from `performers` appearances; each Performer includes name, alias (`as`), role/gender, and the first image URL when available.
        - tags are deduplicated and sorted to maintain consistent ordering.
        - `fingerprints` entries are converted to SceneHash objects; fingerprint `algorithm` is mapped to HashType (unknown algorithms default to PHASH) and duration is preserved.
        - original_query, original_response, and original_parsed_filename are stored on the result for traceability.
        - look_up_site_id is set to the numeric scene id (string) for compatibility.
        
        Parameters:
            scene_data (Dict[str, Any]): The GraphQL scene object returned by the API.
            original_query (str): The GraphQL query string or reference used to fetch this scene (kept for traceability).
            original_response (str): Raw response payload or reference (kept for traceability).
            name_parts (Optional[FileInfo]): Parsed filename parts used as context; stored on the result.
        
        Returns:
            LookedUpFileInfo: A populated LookedUpFileInfo instance representing the scene.
        """
        file_info = LookedUpFileInfo()
        
        # Basic scene information
        file_info.type = SceneType.SCENE
        
        # Use numeric _id for UUID to maintain legacy compatibility
        numeric_id = scene_data.get('_id', scene_data.get('id', ''))
        file_info.uuid = f'scenes/{numeric_id}'
        file_info.guid = scene_data.get('id', '')
        file_info.name = scene_data.get('title', '')
        file_info.description = scene_data.get('details', '')
        file_info.date = scene_data.get('date', '')
        # Extract primary source URL from urls list
        file_info.source_url = None
        if isinstance(scene_data.get('urls'), list) and scene_data['urls']:
            try:
                file_info.source_url = scene_data['urls'][0].get('url')
            except Exception:
                file_info.source_url = None
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
        
        # Studio/site information
        if 'studio' in scene_data and scene_data['studio']:
            studio = scene_data['studio']
            file_info.site = studio.get('name', '')
            if 'parent' in studio and studio['parent']:
                file_info.parent = studio['parent'].get('name', '')
        # TPDB schema shown does not expose network on Scene; leave network as None
        
        # Performers via PerformerAppearance
        if isinstance(scene_data.get('performers'), list):
            for appearance in scene_data['performers']:
                perf = appearance.get('performer') or {}
                performer_name = perf.get('name')
                if not performer_name:
                    continue
                performer = Performer(performer_name)
                performer.alias = appearance.get('as')
                # Gender
                performer.role = perf.get('gender')
                # Image (first image url if available)
                images = perf.get('images') or []
                if isinstance(images, list) and images:
                    first_image = images[0] or {}
                    performer.image = first_image.get('url')
                file_info.performers.append(performer)
        
        # Tags (deduplicated and sorted to match legacy behavior)
        if 'tags' in scene_data:
            tag_names = [tag['name'] for tag in scene_data['tags'] if 'name' in tag]
            # Deduplicate first, then sort to ensure consistent ordering
            file_info.tags = sorted(list(dict.fromkeys(tag_names)))
        
        # Fingerprints -> SceneHash objects
        if isinstance(scene_data.get('fingerprints'), list):
            for fp in scene_data['fingerprints']:
                algo = (fp.get('algorithm') or '').upper()
                try:
                    hash_type = HashType[algo]
                except KeyError:
                    hash_type = HashType.PHASH
                scene_hash = SceneHash(fp.get('hash', ''), hash_type, fp.get('duration'))
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
        Find matching scene metadata for a file by using filename parts and/or a perceptual hash.
        
        Performs a hash-first search against ThePornDB GraphQL fingerprints when a `phash` is provided:
        - Queries PHASH (and optional OSHASH) fingerprints and converts results into LookedUpFileInfo candidates.
        - Attempts to resolve candidates by PHASH/OSHASH intersection, filename-based scoring (title/site/date), majority-of-submissions thresholds, and PHASH-distance thresholds and margins.
        - May mark the outcome as ambiguous when fingerprint distances or close peers prevent a confident single selection.
        
        If no confident PHASH-based match is found (or no `phash` is provided), falls back to a text search:
        - Builds a query from site, name, and date parts and searches scenes via GraphQL, returning converted LookedUpFileInfo results.
        
        Returns ComparisonResults containing zero or more ComparisonResult entries (one confident PHASH-based result when accepted, otherwise evaluated text-search results). The returned ComparisonResults may have its `ambiguous` flag set when fingerprint results were inconclusive.
        
        Parameters documented for clarity:
        - file_name_parts: FileInfo | None — parsed filename metadata (name, site, date) used for scoring and text search.
        - config: NamerConfig — provider configuration (used for thresholds such as phash_accept_distance, phash_unique_threshold, etc.).
        - phash: PerceptualHash | None — perceptual hash object (must expose `.phash`, may include `.oshash` and `.duration`) used for fingerprint-based matching.
        
        Returns:
            ComparisonResults — evaluation results for candidate matches; contains the original `file_name_parts`.
        """
        results: List[LookedUpFileInfo] = []

        if not file_name_parts and not phash:
            return ComparisonResults([], file_name_parts)

        # Helper scoring for filename-based disambiguation
        def score_scene(scene_info: LookedUpFileInfo) -> float:
            """
            Compute a numeric score for how well a scene matches the current filename parts.
            
            Scoring components:
            - Title similarity: rapidfuzz string ratio between the lowercased filename title and scene title (0–100). Falls back to 0 if rapidfuzz is unavailable or comparison fails.
            - Site bonus: +50 if the filename site and scene site are considered matching by self._site_match.
            - Date bonus: +50 if the filename date and scene date are equal according to self._date_match.
            
            Parameters:
                scene_info (LookedUpFileInfo): Scene metadata to score.
            
            Returns:
                float: Combined score (site + date bonuses plus title similarity). Higher values indicate a better match.
            """
            title_score = 0.0
            if file_name_parts and file_name_parts.name and scene_info.name:
                try:
                    import rapidfuzz.fuzz
                    title_score = rapidfuzz.fuzz.ratio(file_name_parts.name.lower(), scene_info.name.lower())
                except Exception:
                    title_score = 0.0
            site_score = 50.0 if (file_name_parts and self._site_match(file_name_parts.site, scene_info.site)) else 0.0
            date_score = 50.0 if (file_name_parts and self._date_match(file_name_parts.date, scene_info.date)) else 0.0
            return site_score + date_score + float(title_score)

        # Hash-first strategy using TPDB GraphQL (findScenesBySceneFingerprints)
        accepted_scene: Optional[LookedUpFileInfo] = None
        if phash:
            try:
                def gql_search_fingerprints(ph: PerceptualHash) -> List[List[LookedUpFileInfo]]:
                    """
                    Search ThePornDB for scenes matching the provided perceptual hash.
                    
                    Performs a GraphQL query grouping fingerprints (PHASH first, then OSHASH if present on `ph`) and converts each returned scene into a LookedUpFileInfo. The result is a list of groups (one per fingerprint group in the request); each group is a list of LookedUpFileInfo objects for scenes that matched that fingerprint group. Returns an empty list for groups with no results or when the GraphQL response is missing/invalid.
                    
                    Parameters:
                        ph (PerceptualHash): PerceptualHash containing at minimum `ph.phash`. If `ph.oshash` exists it will be included as a second fingerprint group.
                    
                    Returns:
                        List[List[LookedUpFileInfo]]: Outer list corresponds to fingerprint groups (PHASH, then optional OSHASH). Each inner list contains LookedUpFileInfo objects for scenes matched for that group.
                    """
                    query = '''
                        query FindByFingerprints($fingerprints: [[FingerprintQueryInput!]!]) {
                            findScenesBySceneFingerprints(fingerprints: $fingerprints) {
                                id
                                title
                                date
                                duration
                                urls { url site { name } }
                                studio { name parent { name } }
                                performers { performer { name gender images { url } urls { url site { name } } } as }
                                tags { name }
                                fingerprints { hash algorithm duration submissions }
                            }
                        }
                    '''
                    groups: List[List[Dict[str, str]]] = []
                    # Group 0: PHASH
                    groups.append([{ 'hash': str(ph.phash), 'algorithm': 'PHASH' }])
                    # Group 1: OSHASH (optional)
                    if getattr(ph, 'oshash', None):
                        groups.append([{ 'hash': ph.oshash, 'algorithm': 'OSHASH' }])

                    data = self._graphql_request(query, { 'fingerprints': groups }, config)
                    out: List[List[LookedUpFileInfo]] = []
                    if data and 'findScenesBySceneFingerprints' in data and isinstance(data['findScenesBySceneFingerprints'], list):
                        for idx, scene_list in enumerate(data['findScenesBySceneFingerprints']):
                            group_infos: List[LookedUpFileInfo] = []
                            if isinstance(scene_list, list):
                                for scene_data in scene_list:
                                    fi = self._graphql_scene_to_fileinfo(
                                        scene_data,
                                        f'gql-fingerprints-group-{idx}',
                                        orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'),
                                        file_name_parts,
                                    )
                                    group_infos.append(fi)
                            out.append(group_infos)
                    return out

                grouped_results = gql_search_fingerprints(phash)
                phash_results: List[LookedUpFileInfo] = grouped_results[0] if len(grouped_results) > 0 else []
                oshash_results: List[LookedUpFileInfo] = grouped_results[1] if len(grouped_results) > 1 else []

                if phash_results or oshash_results:
                    phash_ids = set(fi.guid for fi in phash_results if fi.guid)
                    oshash_ids = set(fi.guid for fi in oshash_results if fi.guid)
                    intersection_ids = phash_ids.intersection(oshash_ids) if phash_ids and oshash_ids else set()

                    combined_results = phash_results + oshash_results
                    # Helper: compute PHASH distance metrics per candidate
                    def phash_metrics(scene_info: LookedUpFileInfo):
                        """
                        Compute the best Hamming distance between the active `phash` and any PHASH entry on a scene, and indicate whether the matching fingerprint also matches duration.
                        
                        This checks scene_info.hashes for entries with HashType.PHASH and a hex length matching the active `phash`. For each compatible fingerprint it computes the Hamming distance to the active `phash` and records whether the fingerprint's duration equals the active `phash` duration. The function returns the smallest distance found and a boolean that is True when that best-distance fingerprint has a matching duration.
                        
                        Parameters:
                            scene_info (LookedUpFileInfo): Scene metadata containing fingerprint hashes to compare.
                        
                        Returns:
                            tuple:
                                - best_distance (int | None): Smallest Hamming distance found, or None if no compatible PHASH fingerprints exist.
                                - duration_matches (bool | None): True if the best-distance fingerprint has matching duration, False if it does not, or None if no compatible fingerprints were present.
                        """
                        ph_len = len(str(phash.phash))
                        distances = []
                        for fp in scene_info.hashes or []:
                            try:
                                fp_type = getattr(fp, 'type', getattr(fp, 'hash_type', None))
                                if fp_type != HashType.PHASH:
                                    continue
                                hex_val = getattr(fp, 'hash', getattr(fp, 'scene_hash', None))
                                if not hex_val or len(hex_val) != ph_len:
                                    continue
                                scene_h = imagehash.hex_to_hash(hex_val)
                                d = phash.phash - scene_h
                                dur = getattr(fp, 'duration', None)
                                duration_ok = (dur == phash.duration) if dur else True
                                distances.append((d, 0 if duration_ok else 1))
                            except Exception:
                                continue
                        if not distances:
                            return (None, None)
                        best_d, dur_pref = min(distances)
                        return (best_d, dur_pref == 0)
                    if intersection_ids:
                        candidates = [fi for fi in combined_results if fi.guid in intersection_ids]
                        candidates_scored = sorted(((c, score_scene(c)) for c in candidates), key=lambda x: x[1], reverse=True)
                        accepted_scene = candidates_scored[0][0] if candidates_scored else candidates[0]
                        logger.info('Accepted scene via combined PHASH + OSHASH intersection (TPDB)')
                    else:
                        # Filename-based disambiguation then majority threshold
                        from collections import Counter
                        id_list = [fi.guid for fi in combined_results if fi.guid]
                        counts = Counter(id_list)
                        unique_ids = list(counts.keys())

                        if len(unique_ids) == 1:
                            accepted_scene = combined_results[0]
                            logger.info(f'Fingerprint match found single unique scene with {len(combined_results)} submissions - returning confident match (TPDB)')
                        else:
                            scored = [(fi, score_scene(fi)) for fi in combined_results]
                            scored.sort(key=lambda x: x[1], reverse=True)
                            if scored:
                                top_scene, top_score = scored[0]
                                second_score = scored[1][1] if len(scored) > 1 else -1.0
                                top_site_match = self._site_match(file_name_parts.site if file_name_parts else None, top_scene.site)
                                top_date_match = self._date_match(file_name_parts.date if file_name_parts else None, top_scene.date)
                                distinct = (top_site_match and top_date_match) or (top_score >= 80.0 and (top_score - second_score) >= 20.0)
                                if distinct:
                                    accepted_scene = top_scene
                                    logger.info('Selected scene by filename-based disambiguation (TPDB)')

                            if not accepted_scene:
                                total = sum(counts.values()) if counts else 0
                                if total > 0 and scored:
                                    id_best: Dict[str, tuple] = {}
                                    for fi, sc in scored:
                                        sid = fi.guid
                                        prev = id_best.get(sid)
                                        if not prev or sc > prev[1]:
                                            id_best[sid] = (fi, sc)
                                    ranked = sorted(((sid, cnt, id_best[sid][1], id_best[sid][0]) for sid, cnt in counts.items()), key=lambda x: (x[1], x[2]), reverse=True)
                                    top_sid, top_cnt, _, top_scene_obj = ranked[0]
                                    fraction = top_cnt / float(total)
                                    threshold = max(0.0, min(1.0, getattr(config, 'phash_unique_threshold', 1.0)))
                                    logger.info(f'Phash majority check (TPDB): top {top_cnt}/{total} = {fraction:.2f}, threshold={threshold:.2f}')
                                    if fraction >= threshold:
                                        accepted_scene = top_scene_obj
                                        logger.info('Accepted scene by majority threshold over fingerprint submissions (TPDB)')

                    # PHASH-first thresholds: accept or mark ambiguous
                    ambiguous = False
                    if not accepted_scene and combined_results:
                        metrics = [(c,)+phash_metrics(c) for c in combined_results]
                        with_dist = [m for m in metrics if m[1] is not None]
                        if with_dist:
                            with_dist.sort(key=lambda x: (x[1], 0 if x[2] else 1))
                            best = with_dist[0]
                            second = with_dist[1] if len(with_dist) > 1 else None
                            best_d = best[1]
                            best_dur_ok = best[2]
                            second_d = second[1] if second else None
                            margin = (second_d - best_d) if (second_d is not None and best_d is not None) else None
                            from collections import Counter
                            id_list = [fi.guid for fi in combined_results if fi.guid]
                            counts = Counter(id_list)
                            total = sum(counts.values()) if counts else 0
                            frac = (counts.most_common(1)[0][1] / float(total)) if total else 0.0
                            accept_d = getattr(config, 'phash_accept_distance', 6)
                            margin_acc = getattr(config, 'phash_distance_margin_accept', 3)
                            frac_acc = getattr(config, 'phash_majority_accept_fraction', 0.7)
                            amb_min = getattr(config, 'phash_ambiguous_min', 7)
                            amb_max = getattr(config, 'phash_ambiguous_max', 12)
                            if best_d is not None and best_d <= accept_d and (best_dur_ok or (margin is not None and margin >= margin_acc) or frac >= frac_acc):
                                accepted_scene = best[0]
                                logger.info('Accepted scene by PHASH distance thresholds (TPDB) best_d=%s margin=%s majority=%.2f', best_d, margin, frac)
                            else:
                                close_peers = [x for x in with_dist[1:4] if x[1] is not None and best_d is not None and (x[1] - best_d) <= 2]
                                if (best_d is not None and amb_min <= best_d <= amb_max) or close_peers:
                                    ambiguous = True
            except Exception as e:
                logger.debug(f'TPDB fingerprint search failed: {e}')

        # If accepted via hash logic, return a single confident phash-based result
        if accepted_scene:
            from namer.comparison_results import ComparisonResult
            nm = 100.0
            dm = True
            sm = True
            if file_name_parts:
                nm = score_scene(accepted_scene)  # includes site/date bonuses; still okay for logging
                dm = self._date_match(file_name_parts.date, accepted_scene.date)
                sm = self._site_match(file_name_parts.site, accepted_scene.site)
            comparison_result = ComparisonResult(
                name=accepted_scene.name or '',
                name_match=float(nm if isinstance(nm, (int, float)) else 100.0),
                date_match=bool(dm),
                site_match=bool(sm),
                name_parts=file_name_parts,
                looked_up=accepted_scene,
                phash_distance=0,
                phash_duration=True,
            )
            return ComparisonResults([comparison_result], file_name_parts)

        # Otherwise, continue with text-based search behavior
        search_terms: List[str] = []
        if file_name_parts:
            if file_name_parts.site:
                search_terms.append(file_name_parts.site)
            if file_name_parts.name:
                search_terms.append(file_name_parts.name)
            if file_name_parts.date:
                search_terms.append(file_name_parts.date)

        if search_terms:
            query_string = ' '.join(search_terms)
            text_results = self._search_scenes(query_string, SceneType.SCENE, config)
            for scene_data in text_results:
                file_info = self._graphql_scene_to_fileinfo(
                    scene_data,
                    query_string,
                    orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'),
                    file_name_parts
                )
                results.append(file_info)

        # Evaluate results using legacy evaluation/weighting for consistency
        import namer.metadataapi as meta_api
        evaluate_match_func = getattr(meta_api, '_ThePornDBProvider__evaluate_match', None) or getattr(meta_api, '__evaluate_match', None)
        match_weight_func = getattr(meta_api, '_ThePornDBProvider__match_weight', None) or getattr(meta_api, '__match_weight', None)

        comparison_results = []
        if evaluate_match_func:
            for fi in results:
                comparison_results.append(evaluate_match_func(file_name_parts, fi, config, phash))
        if match_weight_func:
            comparison_results = sorted(comparison_results, key=match_weight_func, reverse=True)
        # If ambiguous flag computed above, propagate it (only meaningful when hash path ran)
        try:
            return ComparisonResults(comparison_results, file_name_parts, ambiguous=locals().get('ambiguous', False))
        except TypeError:
            cr = ComparisonResults(comparison_results, file_name_parts)
            try:
                setattr(cr, 'ambiguous', locals().get('ambiguous', False))
            except Exception:
                pass
            return cr

    # Lightweight site/date helpers for scoring
    def _site_match(self, query_site: Optional[str], scene_site: Optional[str]) -> bool:
        """
        Return True if query_site is a case-insensitive substring of scene_site.
        
        Both inputs must be non-empty; comparison is performed case-insensitively using simple containment.
        
        Parameters:
            query_site (Optional[str]): Site name extracted from the filename or query.
            scene_site (Optional[str]): Site name from the scene metadata.
        
        Returns:
            bool: True when both arguments are present and query_site.lower() is contained within scene_site.lower(), otherwise False.
        """
        return bool(query_site and scene_site and query_site.lower() in scene_site.lower())

    def _date_match(self, query_date: Optional[str], scene_date: Optional[str]) -> bool:
        """
        Return True if both dates are present and exactly equal.
        
        Parameters:
            query_date (Optional[str]): The date extracted from the filename or query (may be None).
            scene_date (Optional[str]): The scene's date from metadata (may be None).
        
        Returns:
            bool: True when both inputs are non-empty and identical; otherwise False.
        """
        return bool(query_date and scene_date and query_date == scene_date)
    
    def _search_scenes(self, query: str, scene_type: SceneType, config: NamerConfig, page: int = 1) -> List[Dict[str, Any]]:
        """
        Search for scenes via ThePornDB GraphQL API and return raw scene payloads.
        
        Uses the current public schema's `searchScene(term: String!)` query (preferred) to fetch scene records matching `query`. Returns a list of raw scene dictionaries as returned by the GraphQL response; returns an empty list when no matches are found or on request failure. Note: the `scene_type` parameter is accepted for API compatibility but is not used by this implementation; the `page` parameter is currently unused by the GraphQL query.
        """
        # Current schema: searchScene(term: $term)
        search_scene_query = '''
            query SearchScene($term: String!) {
                searchScene(term: $term) {
                    id
                    title
                    date
                    details
                    duration
                    urls { url site { name } }
                    studio { name parent { name } }
                    performers { performer { name gender images { url } urls { url site { name } } } as }
                    tags { name }
                    fingerprints { hash algorithm duration submissions }
                }
            }
        '''
        variables = { 'term': query }
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
        Retrieve complete scene metadata by UUID from ThePornDB and convert it to a LookedUpFileInfo.
        
        The UUID may be in the form "scenes/<id>" or just "<id>"; the numeric id is extracted and used in a GraphQL GetScene query. If the scene is found the response is converted to a LookedUpFileInfo via _graphql_scene_to_fileinfo and returned.
        
        Side effects:
        - If the returned scene payload contains an `isCollected` flag and the provider configuration has `mark_collected` enabled, this method will call _mark_collected(scene_id, config) to mark the scene collected.
        
        Parameters:
            file_name_parts (Optional[FileInfo]): Optional parsed filename parts used to populate compatibility fields in the returned LookedUpFileInfo.
            uuid (str): Scene UUID or id (e.g., "scenes/12345" or "12345").
        
        Returns:
            Optional[LookedUpFileInfo]: Populated LookedUpFileInfo when the scene is found; otherwise None.
        """
        # Extract scene ID from UUID (format: scenes/12345)
        scene_id = uuid
        if '/' in uuid:
            scene_id = uuid.split('/')[-1]
        
        scene_query = '''
            query GetScene($id: ID!) {
                findScene(id: $id) {
                    id
                    title
                    date
                    details
                    duration
                    urls { url site { name } }
                    studio { name parent { name } }
                    performers { performer { name gender images { url } urls { url site { name } } } as }
                    tags { name }
                    fingerprints { hash algorithm duration submissions }
                }
            }
        '''
        
        variables = {'id': scene_id}
        
        response_data = self._graphql_request(scene_query, variables, config)
        
        if response_data and 'findScene' in response_data and response_data['findScene']:
            scene_data = response_data['findScene']
            
            # Mark as collected if needed
            if config.mark_collected and 'isCollected' in scene_data and not scene_data['isCollected']:
                self._mark_collected(scene_id, config)
            
            file_info = self._graphql_scene_to_fileinfo(
                scene_data,
                f'findScene:{scene_id}',
                orjson.dumps(scene_data, option=orjson.OPT_INDENT_2).decode('utf-8'),
                file_name_parts
            )
            
            # Collection status not exposed in schema payload; leave default
            
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
        mutation = '''
            mutation MarkCollected($sceneId: ID!) {
                markSceneCollected(sceneId: $sceneId) {
                    success
                    message
                }
            }
        '''
        
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
        mutation = '''
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
        '''
        
        variables = {
            'sceneId': scene_id,
            'hash': scene_hash.hash,
            'hashType': scene_hash.type.value,
            'duration': scene_hash.duration
        }
        
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
        Retrieve the current authenticated user's basic info from ThePornDB.
        
        Performs a GraphQL query for the authenticated "me" object and returns its payload when available.
        
        Returns:
            dict | None: The user's data (contains at least 'id' and 'name') or None if unavailable.
        """
        user_query = '''
            query GetUser {
                me {
                    id
                    name
                }
            }
        '''
        
        response_data = self._graphql_request(user_query, {}, config)
        
        if response_data and 'me' in response_data:
            return response_data['me']

        return None


# (Removed) Legacy function mappings for backward compatibility
