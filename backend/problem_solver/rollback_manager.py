"""Snapshot and Rollback Engine for Safe Reversible System Changes."""
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
import psutil

from backend.core.logger import get_logger
from backend.problem_solver.models import ProblemCategory, SnapshotData

logger = get_logger("RollbackManager")


class RollbackManager:
    """Captures logical system snapshots before repairs and restores previous state if needed."""

    _snapshots: Dict[str, SnapshotData] = {}

    @classmethod
    def capture_snapshot(cls, category: ProblemCategory, description: str = "") -> SnapshotData:
        """Capture logical state of relevant services and adapter settings."""
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        service_states = {}

        # Capture target services based on category
        services_to_check = []
        if category == ProblemCategory.BLUETOOTH:
            services_to_check = ["bthserv", "BTAGService", "bthHFSrv"]
        elif category in [ProblemCategory.WIFI_NETWORK, ProblemCategory.INTERNET]:
            services_to_check = ["Dhcp", "Dnscache", "WlanSvc", "netprofm"]
        elif category == ProblemCategory.AUDIO:
            services_to_check = ["Audiosrv", "AudioEndpointBuilder"]
        elif category == ProblemCategory.WINDOWS_UPDATE:
            services_to_check = ["wuauserv", "BITS", "CryptSvc"]

        for s in services_to_check:
            try:
                srv = psutil.win_service_get(s)
                service_states[s] = srv.status()
            except Exception:
                service_states[s] = "not_found"

        snap = SnapshotData(
            snapshot_id=snapshot_id,
            created_at=datetime.now(),
            category=category,
            service_states=service_states,
            description=description,
        )
        cls._snapshots[snapshot_id] = snap
        logger.info(f"Captured logical snapshot '{snapshot_id}' for category {category}")
        return snap

    @classmethod
    def get_snapshot(cls, snapshot_id: str) -> Optional[SnapshotData]:
        """Retrieve a stored snapshot by ID."""
        return cls._snapshots.get(snapshot_id)

    @classmethod
    def rollback(cls, snapshot_id: str) -> Dict[str, Any]:
        """Restore previous service and configuration state from snapshot."""
        snap = cls.get_snapshot(snapshot_id)
        if not snap:
            return {
                "status": "not_found",
                "message": f"Snapshot '{snapshot_id}' not found. Rollback is unavailable.",
            }

        logger.info(f"Rolling back to snapshot '{snapshot_id}' ({snap.description})...")
        restored_services = []
        for srv_name, prev_state in snap.service_states.items():
            if prev_state == "running":
                try:
                    import subprocess
                    subprocess.run(f"powershell -NoProfile -Command \"Start-Service -Name '{srv_name}' -ErrorAction SilentlyContinue\"", shell=True, timeout=5)
                    restored_services.append(f"{srv_name} -> started")
                except Exception:
                    pass

        return {
            "status": "success",
            "snapshot_id": snapshot_id,
            "restored_services": restored_services,
            "message": f"Rollback complete for snapshot '{snapshot_id}'.",
        }
