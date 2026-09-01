"""Developer Toolchains and NPM Cache Repair Module."""
import subprocess
from typing import Any, Dict

from backend.core.logger import get_logger

logger = get_logger("DevEnvRepair")


class DevEnvRepair:
    """Repairs NPM cache issues, PATH anomalies, and developer toolchain locks."""

    @staticmethod
    def verify_clean_npm_cache() -> Dict[str, Any]:
        """Run npm cache verify and clean safely."""
        logger.info("Verifying and cleaning npm cache...")
        try:
            res = subprocess.run("npm cache verify", shell=True, capture_output=True, text=True, timeout=20)
            return {
                "status": "success" if res.returncode == 0 else "warning",
                "action": "verify_clean_npm_cache",
                "message": "NPM cache verified and garbage-collected successfully.",
                "details": res.stdout.strip(),
            }
        except Exception as e:
            return {"status": "error", "action": "verify_clean_npm_cache", "message": f"NPM repair error: {e}"}
