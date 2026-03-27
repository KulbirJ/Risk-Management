"""
MITRE ATT&CK TAXII / STIX Sync Service.

Fetches ATT&CK Enterprise data from MITRE and caches it in the local database.

Strategy:
  1. Primary  – download ATT&CK STIX bundle from GitHub (single request, no auth).
  2. Fallback – TAXII 2.1 paginated API at attack-taxii.mitre.org.

The sync is idempotent: running it multiple times is safe.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.config import settings
from ..models.models import (
    AttackTactic, AttackTechnique, AttackSyncStatus, AttackGroup,
    ATTACK_TACTIC_ORDER,
)

logger = logging.getLogger(__name__)

# ─── constants ────────────────────────────────────────────────────────────────
TAXII_ACCEPT = "application/taxii+json;version=2.1"
BUNDLE_TIMEOUT = 60   # seconds – bundle is ~10 MB
TAXII_TIMEOUT  = 30   # seconds per paginated request


class TaxiiSyncService:
    """Fetches and caches MITRE ATT&CK tactics and techniques."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def sync(self, db: Session) -> Dict[str, Any]:
        """
        Full sync: fetch ATT&CK data, upsert into DB, return stats.

        Returns a dict:
          {status, tactics_count, techniques_count, groups_count, error_message}
        """
        status_record = self._get_or_create_sync_status(db)
        status_record.sync_status = "running"
        status_record.error_message = None
        db.commit()

        try:
            objects = self._fetch_stix_objects()
            if not objects:
                raise RuntimeError("No STIX objects fetched – check network connectivity")

            tactics_map = self._upsert_tactics(db, objects)
            techniques_count = self._upsert_techniques(db, objects, tactics_map)
            groups_count = self._upsert_groups(db, objects)

            status_record.sync_status = "completed"
            status_record.last_synced_at = datetime.now(timezone.utc)
            status_record.tactics_count = len(tactics_map)
            status_record.techniques_count = techniques_count
            status_record.source_url = settings.attack_stix_bundle_url
            db.commit()

            logger.info(
                f"ATT&CK sync completed: {len(tactics_map)} tactics, "
                f"{techniques_count} techniques, {groups_count} groups"
            )
            return {
                "status": "completed",
                "tactics_count": len(tactics_map),
                "techniques_count": techniques_count,
                "groups_count": groups_count,
            }

        except Exception as exc:
            logger.error(f"ATT&CK sync failed: {exc}", exc_info=True)
            try:
                status_record.sync_status = "failed"
                status_record.error_message = str(exc)[:500]
                db.commit()
            except Exception:
                db.rollback()
            return {
                "status": "failed",
                "tactics_count": 0,
                "techniques_count": 0,
                "groups_count": 0,
                "error_message": str(exc),
            }

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------

    def _fetch_stix_objects(self) -> List[Dict[str, Any]]:
        """Try GitHub bundle first; fall back to TAXII 2.1 paginated API."""
        logger.info("Fetching ATT&CK STIX bundle from GitHub…")
        try:
            return self._fetch_via_bundle()
        except Exception as bundle_err:
            logger.warning(f"GitHub bundle failed ({bundle_err}); trying TAXII 2.1…")
            return self._fetch_via_taxii()

    def _fetch_via_bundle(self) -> List[Dict[str, Any]]:
        """Download the monolithic STIX bundle JSON from GitHub."""
        resp = requests.get(
            settings.attack_stix_bundle_url,
            timeout=BUNDLE_TIMEOUT,
            headers={"User-Agent": "ThreatRiskAssessmentPlatform/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        objects: List[Dict] = data.get("objects", [])
        logger.info(f"Bundle fetched: {len(objects)} raw STIX objects")
        return objects

    def _fetch_via_taxii(self) -> List[Dict[str, Any]]:
        """
        Fetch objects from MITRE TAXII 2.1 API with cursor-based pagination.
        Filters to only x-mitre-tactic and attack-pattern types.
        """
        headers = {
            "Accept": TAXII_ACCEPT,
            "User-Agent": "ThreatRiskAssessmentPlatform/1.0",
        }
        base_url = settings.attack_taxii_url
        params: Dict[str, Any] = {
            "match[type]": ["attack-pattern", "x-mitre-tactic"],
        }

        all_objects: List[Dict] = []
        next_cursor: Optional[str] = None
        page = 0

        while True:
            page += 1
            if next_cursor:
                params["next"] = next_cursor
            else:
                params.pop("next", None)

            resp = requests.get(base_url, headers=headers, params=params, timeout=TAXII_TIMEOUT)
            resp.raise_for_status()

            body = resp.json()
            page_objects = body.get("objects", [])
            all_objects.extend(page_objects)
            logger.info(f"TAXII page {page}: {len(page_objects)} objects (total {len(all_objects)})")

            next_cursor = body.get("next")
            if not next_cursor or not page_objects:
                break

        logger.info(f"TAXII fetch complete: {len(all_objects)} objects across {page} pages")
        return all_objects

    # ------------------------------------------------------------------
    # Upsert helpers
    # ------------------------------------------------------------------

    def _upsert_tactics(
        self,
        db: Session,
        objects: List[Dict[str, Any]],
    ) -> Dict[str, AttackTactic]:
        """
        Parse x-mitre-tactic objects, upsert into DB.
        Returns a dict keyed by shortname → AttackTactic ORM instance.
        """
        tactics_map: Dict[str, AttackTactic] = {}
        now = datetime.now(timezone.utc)

        for obj in objects:
            if obj.get("type") != "x-mitre-tactic":
                continue
            if obj.get("x_mitre_deprecated") or obj.get("revoked"):
                continue

            stix_id = obj.get("id", "")
            name = obj.get("name", "")
            shortname = obj.get("x_mitre_shortname", "")
            description = obj.get("description", "")

            # Extract external MITRE reference
            mitre_id, url = self._extract_mitre_ref(obj)
            if not mitre_id:
                continue

            existing = db.query(AttackTactic).filter(
                AttackTactic.stix_id == stix_id
            ).first()

            if existing:
                existing.name = name
                existing.shortname = shortname
                existing.description = description
                existing.url = url
                existing.phase_order = ATTACK_TACTIC_ORDER.get(shortname)
                existing.last_synced_at = now
                tactics_map[shortname] = existing
            else:
                tactic = AttackTactic(
                    stix_id=stix_id,
                    mitre_id=mitre_id,
                    name=name,
                    shortname=shortname,
                    description=description,
                    url=url,
                    phase_order=ATTACK_TACTIC_ORDER.get(shortname),
                    last_synced_at=now,
                )
                db.add(tactic)
                db.flush()  # get the generated id
                tactics_map[shortname] = tactic

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise exc

        logger.info(f"Upserted {len(tactics_map)} tactics")
        return tactics_map

    def _upsert_techniques(
        self,
        db: Session,
        objects: List[Dict[str, Any]],
        tactics_map: Dict[str, AttackTactic],
    ) -> int:
        """
        Parse attack-pattern objects, upsert into DB.
        Returns total number of techniques upserted.
        """
        now = datetime.now(timezone.utc)
        count = 0

        # Build a stix_id → technique map (to resolve parent sub-techniques)
        existing_by_stix: Dict[str, AttackTechnique] = {
            t.stix_id: t
            for t in db.query(AttackTechnique).all()
        }

        # First pass: non-subtechniques (so parent IDs can be resolved in pass 2)
        all_patterns = [
            obj for obj in objects
            if obj.get("type") == "attack-pattern"
            and not obj.get("x_mitre_deprecated")
            and not obj.get("revoked")
        ]

        # Sort: parent techniques first
        parents = [o for o in all_patterns if not o.get("x_mitre_is_subtechnique")]
        subs    = [o for o in all_patterns if o.get("x_mitre_is_subtechnique")]

        for obj in parents + subs:
            technique = self._upsert_single_technique(
                db, obj, tactics_map, existing_by_stix, now
            )
            if technique:
                existing_by_stix[technique.stix_id] = technique
                count += 1

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise exc

        logger.info(f"Upserted {count} techniques/sub-techniques")
        return count

    def _upsert_single_technique(
        self,
        db: Session,
        obj: Dict[str, Any],
        tactics_map: Dict[str, AttackTactic],
        existing_by_stix: Dict[str, AttackTechnique],
        now: datetime,
    ) -> Optional[AttackTechnique]:
        """Upsert a single attack-pattern STIX object."""
        stix_id = obj.get("id", "")
        name = obj.get("name", "")
        description = obj.get("description", "")
        detection_text = obj.get("x_mitre_detection", None)
        platforms: List[str] = obj.get("x_mitre_platforms", []) or []
        is_subtechnique: bool = bool(obj.get("x_mitre_is_subtechnique", False))

        # Data sources may be strings or structured objects in different ATT&CK versions
        raw_sources = obj.get("x_mitre_data_sources", []) or []
        data_sources: List[str] = []
        for src in raw_sources:
            if isinstance(src, str):
                data_sources.append(src)
            elif isinstance(src, dict):
                data_sources.append(src.get("name", str(src)))

        # Resolve MITRE ID and URL
        mitre_id, url = self._extract_mitre_ref(obj)
        if not mitre_id:
            return None

        # Resolve primary tactic via kill_chain_phases
        tactic_obj: Optional[AttackTactic] = None
        tactic_shortname: Optional[str] = None
        phases: List[Dict] = obj.get("kill_chain_phases", []) or []
        for phase in phases:
            if phase.get("kill_chain_name") == "mitre-attack":
                sn = phase.get("phase_name", "")
                if sn in tactics_map:
                    tactic_obj = tactics_map[sn]
                    tactic_shortname = sn
                    break

        existing = existing_by_stix.get(stix_id)

        if existing:
            existing.name = name
            existing.description = description
            existing.detection_text = detection_text
            existing.platforms = platforms
            existing.data_sources = data_sources
            existing.url = url
            existing.is_subtechnique = is_subtechnique
            existing.tactic_id = tactic_obj.id if tactic_obj else None
            existing.tactic_shortname = tactic_shortname
            existing.last_synced_at = now
            return existing
        else:
            technique = AttackTechnique(
                stix_id=stix_id,
                mitre_id=mitre_id,
                name=name,
                tactic_id=tactic_obj.id if tactic_obj else None,
                tactic_shortname=tactic_shortname,
                description=description,
                detection_text=detection_text,
                platforms=platforms,
                data_sources=data_sources,
                mitigations=[],
                url=url,
                is_subtechnique=is_subtechnique,
                last_synced_at=now,
            )
            db.add(technique)
            db.flush()
            return technique

    # ------------------------------------------------------------------
    # Groups upsert
    # ------------------------------------------------------------------

    def _upsert_groups(
        self,
        db: Session,
        objects: List[Dict[str, Any]],
    ) -> int:
        """
        Parse intrusion-set objects and their technique relationships,
        then upsert into attack_groups table.
        Returns total number of groups upserted.
        """
        now = datetime.now(timezone.utc)

        # Build group stix_id → list of technique stix_ids from relationship objects
        group_techniques: Dict[str, List[str]] = {}
        for obj in objects:
            if (
                obj.get("type") == "relationship"
                and obj.get("relationship_type") == "uses"
                and not obj.get("x_mitre_deprecated")
                and not obj.get("revoked")
            ):
                src = obj.get("source_ref", "")
                tgt = obj.get("target_ref", "")
                if src.startswith("intrusion-set--") and tgt.startswith("attack-pattern--"):
                    group_techniques.setdefault(src, []).append(tgt)

        # Build existing stix_id → AttackGroup map
        existing_by_stix: Dict[str, AttackGroup] = {
            g.stix_id: g for g in db.query(AttackGroup).all()
        }

        count = 0
        for obj in objects:
            if (
                obj.get("type") != "intrusion-set"
                or obj.get("x_mitre_deprecated")
                or obj.get("revoked")
            ):
                continue

            stix_id: str = obj.get("id", "")
            name: str = obj.get("name", "")
            if not stix_id or not name:
                continue

            # Aliases: MITRE stores them directly on the object
            raw_aliases: List[str] = obj.get("aliases", []) or []
            # Remove the group name itself from aliases list
            aliases = [a for a in raw_aliases if a != name]

            description: str = obj.get("description", "") or ""

            # URL from external references
            url = ""
            for ref in obj.get("external_references", []):
                if ref.get("source_name") == "mitre-attack":
                    url = ref.get("url", "")
                    break

            # Dates – MITRE uses ISO strings like "2017-05-31T21:31:48.197Z"
            first_seen: Optional[str] = obj.get("created", "")[:10] or None
            last_seen: Optional[str] = obj.get("modified", "")[:10] or None

            # Technique STIX IDs this group uses
            technique_ids: List[str] = group_techniques.get(stix_id, [])

            # Target sectors — MITRE STIX doesn't have a standard field for this.
            # Use x_mitre_domains / empty list (can be enriched via OTX later).
            target_sectors: List[str] = []

            existing = existing_by_stix.get(stix_id)
            if existing:
                existing.name = name
                existing.aliases = aliases
                existing.description = description[:2000] if description else None
                existing.technique_ids = technique_ids
                existing.target_sectors = target_sectors
                existing.first_seen = first_seen
                existing.last_seen = last_seen
                existing.url = url
                existing.last_synced_at = now
            else:
                group = AttackGroup(
                    stix_id=stix_id,
                    name=name,
                    aliases=aliases,
                    description=description[:2000] if description else None,
                    technique_ids=technique_ids,
                    target_sectors=target_sectors,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    url=url,
                    last_synced_at=now,
                )
                db.add(group)
            count += 1

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise exc

        logger.info(f"Upserted {count} ATT&CK groups")
        return count

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_mitre_ref(obj: Dict[str, Any]) -> tuple[str, str]:
        """Extract (mitre_id, url) from STIX external_references."""
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                return ref.get("external_id", ""), ref.get("url", "")
        return "", ""

    @staticmethod
    def _get_or_create_sync_status(db: Session) -> AttackSyncStatus:
        record = db.query(AttackSyncStatus).first()
        if not record:
            record = AttackSyncStatus(sync_status="never")
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    def needs_refresh(self, db: Session) -> bool:
        """Return True if the cache is stale or has never been populated."""
        record = db.query(AttackSyncStatus).first()
        if not record or not record.last_synced_at:
            return True
        if record.sync_status != "completed":
            return True
        age_days = (datetime.now(timezone.utc) - record.last_synced_at).days
        return age_days >= settings.attack_cache_ttl_days


# Module-level singleton
taxii_sync_service = TaxiiSyncService()
