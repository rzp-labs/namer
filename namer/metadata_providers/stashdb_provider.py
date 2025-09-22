"""
StashDB GraphQL metadata provider implementation.

This provider interfaces with StashDB's GraphQL API to provide
metadata for adult content, mapping results to namer's data structures.
"""

from pathlib import Path
import os
from typing import Any, Dict, List, Optional

import orjson
from loguru import logger
from orjson import JSONDecodeError

from namer.comparison_results import ComparisonResult, ComparisonResults, HashType, LookedUpFileInfo, Performer, SceneHash, SceneType
from namer.configuration import NamerConfig
from namer.fileinfo import FileInfo
from namer.http import Http, RequestType
from namer.metadata_providers.provider import BaseMetadataProvider
from namer.videophash import PerceptualHash, imagehash


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
        Find metadata matches for a file using filename parts and/or a perceptual hash.
        
        Performs a text search when filename parts are available and, if a PerceptualHash is supplied,
        performs fingerprint lookups (PHASH and OSHASH) and a multi-step disambiguation to produce
        candidate matches. Fingerprint logic may:
        - prefer scenes found by both PHASH and OSHASH,
        - score candidates by filename/site/date alignment,
        - apply configurable distance/margin/majority thresholds to accept a single confident match,
        - otherwise surface multiple candidates and mark the result ambiguous.
        
        If a single confident fingerprint match is accepted, the returned ComparisonResults will contain
        one ComparisonResult with phash_distance set to 0 and phash_duration set to True. Results are
        sorted by match weight before being returned.
        
        Parameters:
            file_name_parts (Optional[FileInfo]): Parsed filename metadata (name, date, site) used to
                score and disambiguate text and fingerprint matches.
            phash (Optional[PerceptualHash]): Optional perceptual hash used to query fingerprints and
                compute phash_distance/phash_duration metrics for candidates.
        
        Returns:
            ComparisonResults: A container of ComparisonResult entries sorted by match quality. The
            container's ambiguous flag will be True if fingerprint disambiguation could not produce a
            single confident match.
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
            try:
                # Query by PHASH and OSHASH (if available) separately
                phash_results: List[LookedUpFileInfo] = []
                oshash_results: List[LookedUpFileInfo] = []
                try:
                    phash_results = self._search_by_fingerprint(str(phash.phash), 'PHASH', config)
                except Exception as e:
                    logger.debug(f"PHASH search failed: {e}")

                if getattr(phash, 'oshash', None):
                    try:
                        oshash_results = self._search_by_fingerprint(phash.oshash, 'OSHASH', config)
                    except Exception as e:
                        logger.debug(f"OSHASH search failed: {e}")

                combined_results = phash_results + oshash_results
                if combined_results:
                    # Helper: compute per-candidate PHASH distance and duration match
                    def phash_metrics(scene_info: LookedUpFileInfo) -> tuple:
                        """
                        Compute the closest PHASH distance between the current `phash` (captured from outer scope) and the PHASH fingerprints found on `scene_info`.
                        
                        This inspects `scene_info.hashes` for entries that represent PHASH fingerprints (handles attributes named `type`/`hash_type` and `hash`/`scene_hash`), skips fingerprints with mismatched hex length, converts hex to imagehash and computes the Hamming distance to `phash.phash`. Duration is considered: if a fingerprint has a `duration` attribute it must equal `phash.duration` to count as a duration match; missing duration is treated as a match. The function returns the smallest distance found and whether that best match has a matching duration.
                        
                        Parameters:
                            scene_info (LookedUpFileInfo): LookedUpFileInfo whose `hashes` will be searched for PHASH entries.
                        
                        Returns:
                            tuple:
                                - (int | None): the smallest Hamming distance between `phash` and any compatible PHASH on `scene_info`, or None if no compatible PHASH was found.
                                - (bool | None): True if the selected best match has a matching duration, False if it does not, or None if no compatible PHASH was found.
                        
                        Notes:
                            - Any exceptions raised while processing individual fingerprints are ignored; they do not stop the overall computation.
                            - The function relies on an outer-scope `phash` variable and returns (None, None) if that `phash` is falsy.
                        """
                        if not phash:
                            return (None, None)
                        phash_len = len(str(phash.phash))
                        distances: List[tuple] = []
                        for fp in scene_info.hashes or []:
                            try:
                                # Normalize attribute names across models
                                fp_type = getattr(fp, 'type', getattr(fp, 'hash_type', None))
                                if fp_type != HashType.PHASH:
                                    continue
                                hex_val = getattr(fp, 'hash', getattr(fp, 'scene_hash', None))
                                if not hex_val:
                                    continue
                                if len(hex_val) != phash_len:
                                    continue
                                scene_h = imagehash.hex_to_hash(hex_val)
                                d = phash.phash - scene_h
                                dur = getattr(fp, 'duration', None)
                                duration_match = (dur == phash.duration) if dur else True
                                distances.append((d, 0 if duration_match else 1))
                            except Exception:
                                continue
                        if not distances:
                            return (None, None)
                        best_d, duration_pref = min(distances)
                        return (best_d, duration_pref == 0)
                    # Prefer scenes that appear in BOTH PHASH and OSHASH results
                    phash_ids = set([fi.guid for fi in phash_results if fi.guid])
                    oshash_ids = set([fi.guid for fi in oshash_results if fi.guid])
                    intersection_ids = phash_ids.intersection(oshash_ids)

                    accepted_scene: Optional[LookedUpFileInfo] = None
                    if intersection_ids:
                        # If both hashes point to the same scene(s), pick the best one by filename scoring with keyword alignment
                        candidates = [fi for fi in combined_results if fi.guid in intersection_ids]
                        def score_scene(scene_info: LookedUpFileInfo) -> float:
                            """
                            Compute a composite score for a candidate scene based on name similarity, site match, and date match.
                            
                            The score is the sum of:
                            - title similarity (0–100) from comparing the file's name and the scene's title,
                            - site match (50 if the file's configured site appears in the scene's site, otherwise 0),
                            - date match (50 if the file's date equals the scene's date, otherwise 0).
                            
                            Parameters:
                                scene_info (LookedUpFileInfo): Candidate scene to score.
                            
                            Returns:
                                float: Higher values indicate a better match (maximum possible score is 200).
                            """
                            title_score = self._calculate_name_match(file_name_parts.name, scene_info.name) if (file_name_parts and file_name_parts.name) else 0.0
                            site_score = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, scene_info.site) else 0.0
                            date_score = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, scene_info.date) else 0.0
                            return site_score + date_score + float(title_score)
                        scored = sorted(((c, score_scene(c)) for c in candidates), key=lambda x: x[1], reverse=True)
                        # DEBUG: Log per-candidate scores for intersection
                        if scored:
                            for idx, (c, sc) in enumerate(scored):
                                if idx >= 3:
                                    break
                                try:
                                    ts = self._calculate_name_match(file_name_parts.name, c.name) if (file_name_parts and file_name_parts.name) else 0.0
                                    ss = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, c.site) else 0.0
                                    ds = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, c.date) else 0.0
                                    logger.debug(f"Intersection score: id={c.guid} title='{c.name}' site='{c.site}' date='{c.date}' -> title={ts:.1f} site={ss:.1f} date={ds:.1f} total={sc:.1f}")
                                except Exception:
                                    pass
                        # Only accept automatically if the top score is distinctly higher than the next (to avoid ambiguous auto-pick)
                        if scored:
                            accepted_scene = scored[0][0]
                            if len(scored) > 1:
                                margin = scored[0][1] - scored[1][1]
                                logger.debug(f"Intersection decision margin={margin:.1f}")
                                if margin < 25.0:
                                    # too close; treat as ambiguous and continue heuristics below
                                    accepted_scene = None
                        if accepted_scene:
                            logger.info("Accepted scene via combined PHASH + OSHASH intersection (filename-informed)")
                        # If still ambiguous after intersection scoring, fall back to full disambiguation on combined_results
                        if not accepted_scene:
                            from collections import Counter
                            id_list = [scene_info.guid for scene_info in combined_results if scene_info.guid]
                            counts = Counter(id_list)
                            unique_scene_ids = list(counts.keys())
                            logger.debug(f"Ambiguous intersection; falling back. Candidate ID counts: {dict(counts)}")
                            def score_scene(scene_info: LookedUpFileInfo) -> float:
                                """
                                Compute a numeric relevance score for a candidate scene by combining name similarity, site match, and date match.
                                
                                Detailed behavior:
                                - Title/name match uses self._calculate_name_match against the current file_name_parts name (returns 0–100).
                                - Site match contributes 50.0 if the query site appears in the scene site (via self._compare_sites), otherwise 0.0.
                                - Date match contributes 50.0 if the query date equals the scene date (via self._compare_dates), otherwise 0.0.
                                
                                Parameters:
                                    scene_info (LookedUpFileInfo): Candidate scene to score.
                                
                                Returns:
                                    float: Combined score where higher values indicate a better match.
                                """
                                title_score = self._calculate_name_match(file_name_parts.name, scene_info.name) if (file_name_parts and file_name_parts.name) else 0.0
                                site_score = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, scene_info.site) else 0.0
                                date_score = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, scene_info.date) else 0.0
                                return site_score + date_score + float(title_score)
                            if len(unique_scene_ids) == 1:
                                accepted_scene = combined_results[0]
                                logger.info(f"Fingerprint match found single unique scene with {len(combined_results)} submissions - returning confident match")
                            else:
                                scored = [(scene_info, score_scene(scene_info)) for scene_info in combined_results]
                                scored.sort(key=lambda x: x[1], reverse=True)
                                # DEBUG: Log per-candidate scores
                                for idx, (c, sc) in enumerate(scored):
                                    if idx >= 3:
                                        break
                                    try:
                                        ts = self._calculate_name_match(file_name_parts.name, c.name) if (file_name_parts and file_name_parts.name) else 0.0
                                        ss = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, c.site) else 0.0
                                        ds = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, c.date) else 0.0
                                        logger.debug(f"Combined score: id={c.guid} title='{c.name}' site='{c.site}' date='{c.date}' -> title={ts:.1f} site={ss:.1f} date={ds:.1f} total={sc:.1f}")
                                    except Exception:
                                        pass
                                if scored:
                                    top_scene, top_score = scored[0]
                                    second_score = scored[1][1] if len(scored) > 1 else -1.0
                                    top_site_match = self._compare_sites(file_name_parts.site if file_name_parts else None, top_scene.site)
                                    top_date_match = self._compare_dates(file_name_parts.date if file_name_parts else None, top_scene.date)
                                    distinct = False
                                    if top_site_match and top_date_match:
                                        distinct = True
                                    elif top_score >= 80.0 and (top_score - second_score) >= 20.0:
                                        distinct = True
                                    if distinct:
                                        accepted_scene = top_scene
                                        logger.info("Selected scene by filename-based disambiguation: site/date/title scoring")
                                if not accepted_scene:
                                    total = sum(counts.values()) if counts else 0
                                    if total > 0 and scored:
                                        id_best: Dict[str, tuple] = {}
                                        for scene_info, sc in scored:
                                            sid = scene_info.guid
                                            prev = id_best.get(sid)
                                            if not prev or sc > prev[1]:
                                                id_best[sid] = (scene_info, sc)
                                        ranked = sorted(((sid, cnt, id_best[sid][1], id_best[sid][0]) for sid, cnt in counts.items()), key=lambda x: (x[1], x[2]), reverse=True)
                                        top_sid, top_cnt, _, top_scene_obj = ranked[0]
                                        fraction = top_cnt / float(total)
                                        threshold = max(0.0, min(1.0, getattr(config, 'phash_unique_threshold', 1.0)))
                                        logger.info(f"Phash majority check: top {top_cnt}/{total} = {fraction:.2f}, threshold={threshold:.2f}")
                                        if fraction >= threshold:
                                            accepted_scene = top_scene_obj
                                            logger.info("Accepted scene by majority threshold over fingerprint submissions")
                    else:
                        # No immediate intersection; continue with existing logic on combined set
                        from collections import Counter
                        id_list = [scene_info.guid for scene_info in combined_results if scene_info.guid]
                        counts = Counter(id_list)
                        unique_scene_ids = list(counts.keys())

                        # Helper to score disambiguation based on filename parts
                        def score_scene(scene_info: LookedUpFileInfo) -> float:
                            """
                            Compute a composite score for a candidate scene based on name similarity, site match, and date match.
                            
                            The score is the sum of:
                            - title similarity (0–100) from comparing the file's name and the scene's title,
                            - site match (50 if the file's configured site appears in the scene's site, otherwise 0),
                            - date match (50 if the file's date equals the scene's date, otherwise 0).
                            
                            Parameters:
                                scene_info (LookedUpFileInfo): Candidate scene to score.
                            
                            Returns:
                                float: Higher values indicate a better match (maximum possible score is 200).
                            """
                            title_score = self._calculate_name_match(file_name_parts.name, scene_info.name) if (file_name_parts and file_name_parts.name) else 0.0
                            site_score = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, scene_info.site) else 0.0
                            date_score = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, scene_info.date) else 0.0
                            return site_score + date_score + float(title_score)

                        if len(unique_scene_ids) == 1:
                            accepted_scene = combined_results[0]
                            logger.info(f"Fingerprint match found single unique scene with {len(combined_results)} submissions - returning confident match")
                        else:
                            # 1) Try filename-based disambiguation
                            scored = [(scene_info, score_scene(scene_info)) for scene_info in combined_results]
                            scored.sort(key=lambda x: x[1], reverse=True)
                            # DEBUG: Log per-candidate scores for non-intersection
                            for idx, (c, sc) in enumerate(scored):
                                if idx >= 3:
                                    break
                                try:
                                    ts = self._calculate_name_match(file_name_parts.name, c.name) if (file_name_parts and file_name_parts.name) else 0.0
                                    ss = 50.0 if self._compare_sites(file_name_parts.site if file_name_parts else None, c.site) else 0.0
                                    ds = 50.0 if self._compare_dates(file_name_parts.date if file_name_parts else None, c.date) else 0.0
                                    logger.debug(f"Fallback score: id={c.guid} title='{c.name}' site='{c.site}' date='{c.date}' -> title={ts:.1f} site={ss:.1f} date={ds:.1f} total={sc:.1f}")
                                except Exception:
                                    pass
                            if scored:
                                top_scene, top_score = scored[0]
                                second_score = scored[1][1] if len(scored) > 1 else -1.0
                                # Consider distinct if strong margin or strong site+date match
                                top_site_match = self._compare_sites(file_name_parts.site if file_name_parts else None, top_scene.site)
                                top_date_match = self._compare_dates(file_name_parts.date if file_name_parts else None, top_scene.date)
                                distinct = False
                                if top_site_match and top_date_match:
                                    distinct = True
                                elif top_score >= 80.0 and (top_score - second_score) >= 20.0:
                                    distinct = True
                                if distinct:
                                    accepted_scene = top_scene
                                    logger.info("Selected scene by filename-based disambiguation: site/date/title scoring")

                            # 2) If still ambiguous, apply frequency threshold
                            if not accepted_scene:
                                total = sum(counts.values()) if counts else 0
                                if total > 0:
                                    # Choose the majority scene by count (break ties using filename score)
                                    id_best = {}
                                    for scene_info, sc in scored:
                                        sid = scene_info.guid
                                        prev = id_best.get(sid)
                                        if not prev or sc > prev[1]:
                                            id_best[sid] = (scene_info, sc)

                                    ranked = sorted(((sid, cnt, id_best[sid][1], id_best[sid][0]) for sid, cnt in counts.items()), key=lambda x: (x[1], x[2]), reverse=True)
                                    if ranked:
                                        top_sid, top_cnt, _, top_scene_obj = ranked[0]
                                        fraction = top_cnt / float(total)
                                        threshold = max(0.0, min(1.0, getattr(config, 'phash_unique_threshold', 1.0)))
                                        logger.info(f"Phash majority check: top {top_cnt}/{total} = {fraction:.2f}, threshold={threshold:.2f}")
                                        if fraction >= threshold:
                                            accepted_scene = top_scene_obj
                                            logger.info("Accepted scene by majority threshold over fingerprint submissions")

                        # PHASH-first acceptance/ambiguity using configured thresholds
                        if not accepted_scene and combined_results:
                            # Compute distances for all candidates
                            metrics = []
                            for c in combined_results:
                                d, dur_ok = phash_metrics(c)
                                metrics.append((c, d, dur_ok))
                            # Filter to those with distances
                            with_dist = [m for m in metrics if m[1] is not None]
                            if with_dist:
                                with_dist.sort(key=lambda x: (x[1], 0 if x[2] else 1))
                                best = with_dist[0]
                                second = with_dist[1] if len(with_dist) > 1 else None
                                best_d = best[1]
                                best_dur_ok = best[2]
                                second_d = second[1] if second else None
                                margin = (second_d - best_d) if (second_d is not None and best_d is not None) else None
                                # Majority stats
                                from collections import Counter
                                id_list = [scene_info.guid for scene_info in combined_results if scene_info.guid]
                                counts = Counter(id_list)
                                total = sum(counts.values()) if counts else 0
                                frac = 0.0
                                if total:
                                    top_sid, top_cnt = counts.most_common(1)[0]
                                    frac = top_cnt / float(total)
                                # Thresholds
                                accept_d = getattr(config, 'phash_accept_distance', 6)
                                margin_acc = getattr(config, 'phash_distance_margin_accept', 3)
                                frac_acc = getattr(config, 'phash_majority_accept_fraction', 0.7)
                                amb_min = getattr(config, 'phash_ambiguous_min', 7)
                                amb_max = getattr(config, 'phash_ambiguous_max', 12)
                                # Accept if within accept_d and either duration OK or margin/majority strong
                                if best_d is not None and best_d <= accept_d and (
                                    best_dur_ok or (margin is not None and margin >= margin_acc) or (frac >= frac_acc)
                                ):
                                    accepted_scene = best[0]
                                    logger.info("Accepted scene by PHASH distance thresholds (best_d={}, margin={}, majority={:.2f})", best_d, margin, frac)
                                else:
                                    # Ambiguous if best in [amb_min, amb_max] or multiple within small margin
                                    close_peers = [x for x in with_dist[1:4] if x[1] is not None and best_d is not None and (x[1] - best_d) <= 2]
                                    if (best_d is not None and amb_min <= best_d <= amb_max) or close_peers:
                                        ambiguous = True

                    # If accepted, produce a single confident ComparisonResult and clear others
                    if accepted_scene:
                        results.clear()
                        # Compute site/date/name metrics for logging purposes
                        nm = self._calculate_name_match(file_name_parts.name, accepted_scene.name) if (file_name_parts and file_name_parts.name) else 100.0
                        dm = self._compare_dates(file_name_parts.date if file_name_parts else None, accepted_scene.date) if file_name_parts else True
                        sm = self._compare_sites(file_name_parts.site if file_name_parts else None, accepted_scene.site) if file_name_parts else True
                        # PHASH metrics for accepted: force is_match() via phash
                        # by setting phash_distance=0 and phash_duration=True
                        comparison_result = ComparisonResult(
                            name=accepted_scene.name or '',
                            name_match=float(nm),
                            date_match=bool(dm),
                            site_match=bool(sm),
                            name_parts=file_name_parts,
                            looked_up=accepted_scene,
                            phash_distance=0,
                            phash_duration=True,
                        )
                        results.append(comparison_result)
                    else:
                        # No decisive pick; surface candidates to allow orchestrator to flag ambiguous
                        for scene_info in combined_results:
                            d, dur_ok = phash_metrics(scene_info)
                            comparison_result = ComparisonResult(
                                name=scene_info.name or '',
                                name_match=self._calculate_name_match(file_name_parts.name, scene_info.name) if (file_name_parts and file_name_parts.name) else 0.0,
                                date_match=self._compare_dates(file_name_parts.date if file_name_parts else None, scene_info.date) if file_name_parts else False,
                                site_match=self._compare_sites(file_name_parts.site if file_name_parts else None, scene_info.site) if file_name_parts else False,
                                name_parts=file_name_parts,
                                looked_up=scene_info,
                                phash_distance=d,
                                phash_duration=dur_ok,
                            )
                            results.append(comparison_result)
                        ambiguous = True
                
            except Exception as e:
                logger.debug(f"Fingerprint search failed: {e}")
        
        # Sort results by quality
        results = sorted(results, key=self._calculate_match_weight, reverse=True)

        # Mark as ambiguous if we explicitly detected ambiguity above
        try:
            return ComparisonResults(results, file_name_parts, ambiguous=locals().get('ambiguous', False))
        except TypeError:
            # Backward compatibility if dataclass signature differs
            cr = ComparisonResults(results, file_name_parts)
            try:
                setattr(cr, 'ambiguous', locals().get('ambiguous', False))
            except Exception:
                pass
            return cr
    
    def get_complete_info(self, file_name_parts: Optional[FileInfo], uuid: str, config: NamerConfig) -> Optional[LookedUpFileInfo]:
        """
        Retrieve full metadata for a single scene from StashDB by UUID.
        
        This issues a GraphQL `findScene` query (requesting id, title, date, urls, details, duration,
        images, studio/parent, performers, tags, and fingerprints) and maps the returned scene
        object to a LookedUpFileInfo via _map_stashdb_scene_to_fileinfo.
        
        Parameters:
            uuid (str): Scene identifier or UUID. If the value contains slashes (e.g. "scenes/{id}"),
                the final path segment is used as the GraphQL ID.
            file_name_parts (Optional[FileInfo]): Optional filename-derived context (not used by the query).
        
        Returns:
            Optional[LookedUpFileInfo]: Mapped scene metadata on success, or None if the scene was not found or the query failed.
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
        Search StashDB for scenes matching a text term and return mapped LookedUpFileInfo results.
        
        Performs a GraphQL search using the provided text term and maps each returned scene to a LookedUpFileInfo. The provider always searches scenes (the provided scene_type is ignored). When mapping succeeds, the method will attempt to attach `original_query` and `original_response` JSON to each returned LookedUpFileInfo for debugging/audit purposes.
        
        Parameters:
            query (str): Text search term sent to StashDB.
            scene_type (SceneType): Declared target type (ignored; search always queries scenes).
            page (int): Reserved paging parameter (currently unused).
        
        Returns:
            List[LookedUpFileInfo]: Mapped search results (may be empty).
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
                        try:
                            file_info.original_query = f"searchScene:{query}"
                            file_info.original_response = orjson.dumps(scene, option=orjson.OPT_INDENT_2).decode('utf-8')
                        except Exception:
                            pass
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
        Note: This query may fail if the token doesn't have sufficient permissions.
        We return a placeholder to allow watchdog to start even if this fails.
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
        if response and 'data' in response and response['data'] and response['data']['me']:
            return response['data']['me']
        
        # If me query fails but we have a token, return placeholder user info
        # to allow watchdog to continue running. Search functionality will still work.
        if config.stashdb_token:
            logger.warning("StashDB 'me' query failed, but token is configured. Continuing with placeholder user info.")
            return {
                'id': 'unknown',
                'name': 'StashDB User (me query unavailable)',
                'roles': []
            }
        
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
            # StashDB uses APIKey header for authentication (not Bearer token)
            headers['APIKey'] = config.stashdb_token
        
        data = orjson.dumps(query)
        # Endpoint resolution order: env > config override > built-in default
        endpoint = os.environ.get('STASHDB_ENDPOINT') or (config.stashdb_endpoint or '').strip() or 'https://stashdb.org/graphql'
        http = Http.request(RequestType.POST, endpoint, cache_session=config.cache_session, headers=headers, data=data)
        
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
        Map a StashDB scene object to a LookedUpFileInfo populated with the provider's expected fields.
        
        The function extracts and translates common StashDB scene fields into the LookedUpFileInfo model:
        - id -> uuid ("scenes/{id}") and guid
        - title, details, date -> name, description, date
        - urls[0].url -> source_url (first entry only)
        - duration -> duration
        - studio.name -> site; studio.parent.name -> parent (if present)
        - images[0].url -> poster_url (first entry only)
        - performers[] -> Performer entries using performer.name, performer.gender -> role, joined aliases -> alias, and images[0].url -> image
        - tags[] -> tags (list of tag.name)
        - fingerprints[] -> SceneHash entries for PHASH fingerprints (algorithm "PHASH" only); SceneHash.scene_hash and duration are populated
        
        Parameters:
            scene (Dict[str, Any]): A StashDB scene dictionary expected to contain keys such as 'id', 'title', 'details',
                'date', 'urls', 'duration', 'studio', 'images', 'performers', 'tags', and 'fingerprints'.
            config (NamerConfig): Provider configuration (not used for field mapping; passed for callers' context).
        
        Returns:
            LookedUpFileInfo: A LookedUpFileInfo instance populated from the provided scene. Never returns None.
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
                        scene_hash=fingerprint.get('hash', ''),
                        hash_type=HashType.PHASH,
                        duration=fingerprint.get('duration')
                    )
                    file_info.hashes.append(scene_hash)
        
        return file_info
    
    def _search_by_fingerprint(self, hash_value: str, algorithm: str, config: NamerConfig) -> List[LookedUpFileInfo]:
        """
        Search StashDB for scenes matching a fingerprint (PHASH or OSHASH) and map results to LookedUpFileInfo objects.
        
        Performs a GraphQL findSceneByFingerprint query using the provided hash and algorithm, maps any returned scene or list of scenes to LookedUpFileInfo via _map_stashdb_scene_to_fileinfo, and returns the mapped results.
        
        Parameters:
            hash_value (str): Fingerprint value to search for.
            algorithm (str): Fingerprint algorithm identifier (e.g., "PHASH" or "OSHASH").
            config: Configuration object (not documented here — passed through to network/query helpers).
        
        Returns:
            List[LookedUpFileInfo]: A list of mapped scene results (empty if no matches). Each returned LookedUpFileInfo will include original_query and original_response fields when those can be serialized successfully.
        """
        query = {
            'query': '''
                query SearchByFingerprint($hash: String!, $algorithm: FingerprintAlgorithm!) {
                    findSceneByFingerprint(fingerprint: {hash: $hash, algorithm: $algorithm}) {
                        id
                        title
                        date
                        urls { url }
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
                'hash': hash_value,
                'algorithm': algorithm
            }
        }
        
        response = self._execute_graphql_query(query, config)
        results = []
        
        if response and 'data' in response and response['data'] and 'findSceneByFingerprint' in response['data']:
            scenes = response['data']['findSceneByFingerprint']
            if scenes:
                # StashDB returns an array of scenes for fingerprint matches
                if isinstance(scenes, list):
                    for scene in scenes:
                        file_info = self._map_stashdb_scene_to_fileinfo(scene, config)
                        if file_info:
                            try:
                                file_info.original_query = f"findSceneByFingerprint:{algorithm}:{hash_value}"
                                file_info.original_response = orjson.dumps(scene, option=orjson.OPT_INDENT_2).decode('utf-8')
                            except Exception:
                                pass
                        if file_info:
                            results.append(file_info)
                else:
                    # Handle case where it might return a single scene object
                    file_info = self._map_stashdb_scene_to_fileinfo(scenes, config)
                    if file_info:
                        try:
                            file_info.original_query = f"findSceneByFingerprint:{algorithm}:{hash_value}"
                            file_info.original_response = orjson.dumps(scenes, option=orjson.OPT_INDENT_2).decode('utf-8')
                        except Exception:
                            pass
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
