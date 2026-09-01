"""Safe File Transfer Subsystem for JARVIS.

Protects against accidental, unconfirmed, or unsafe file sending:
- Generates 2-step transfer preview (filename, file size, recipient, channel).
- Requires explicit user physical/voice confirmation (Thumbs Up or 'Yes').
- Blocks sensitive system credentials (.env, passwords, keys, tokens, SSH keys).
"""

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.core.logger import get_logger

logger = get_logger("FileTransferManager")

# Forbidden file patterns for safe file sending
FORBIDDEN_FILE_PATTERNS = [
    ".env", "id_rsa", "id_ed25519", ".pem", ".key", "password", "passwords",
    "credentials", "token", "auth_token", "cookie", "cookies", "shadow", ".keystore"
]


class FileTransferRequest(BaseModel):
    """File transfer intent model."""
    file_path: str
    recipient: str
    channel: str = "WhatsApp"
    confirmed: bool = False


class FileTransferPreview(BaseModel):
    """2-step confirmation preview for file transfer."""
    filename: str
    file_size_formatted: str
    file_size_bytes: int
    recipient: str
    channel: str
    requires_confirmation: bool = True
    is_safe: bool = True
    safety_message: str = ""
    prompt_message: str = ""


class FileTransferManager:
    """Manages file transfer previews, safety checks, and 2-step confirmations."""

    def __init__(self):
        self.pending_transfer: Optional[FileTransferRequest] = None

    def is_file_safe_to_send(self, file_path: str) -> Tuple[bool, str]:
        """Check if file path contains sensitive credentials or system files."""
        basename = os.path.basename(file_path).lower()
        full_path_low = file_path.lower()

        for pattern in FORBIDDEN_FILE_PATTERNS:
            if pattern in basename or pattern in full_path_low:
                return False, f"File '{basename}' contains sensitive pattern '{pattern}' and cannot be sent automatically for safety."

        return True, "File path is safe for transfer."

    def prepare_transfer(self, file_path: str, recipient: str, channel: str = "WhatsApp") -> FileTransferPreview:
        """Build 2-step confirmation preview before sending file."""
        basename = os.path.basename(file_path)
        size_bytes = 0
        size_formatted = "Unknown Size"

        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                size_formatted = f"{size_bytes} Bytes"
            elif size_bytes < 1024 * 1024:
                size_formatted = f"{round(size_bytes / 1024, 1)} KB"
            else:
                size_formatted = f"{round(size_bytes / (1024 * 1024), 2)} MB"

        is_safe, safety_msg = self.is_file_safe_to_send(file_path)

        if is_safe:
            self.pending_transfer = FileTransferRequest(
                file_path=file_path,
                recipient=recipient,
                channel=channel,
                confirmed=False,
            )
            prompt = (
                f"Ready to send: {basename} ({size_formatted})\n"
                f"To: {recipient}\n"
                f"Via: {channel}\n\n"
                f"Thumbs Up (or 'Yes') to confirm, Closed Fist (or 'No') to cancel."
            )
        else:
            self.pending_transfer = None
            prompt = f"Transfer Blocked: {safety_msg}"

        return FileTransferPreview(
            filename=basename,
            file_size_formatted=size_formatted,
            file_size_bytes=size_bytes,
            recipient=recipient,
            channel=channel,
            requires_confirmation=True,
            is_safe=is_safe,
            safety_message=safety_msg,
            prompt_message=prompt,
        )

    def confirm_pending_transfer(self) -> Optional[FileTransferRequest]:
        """Confirm and return pending file transfer request."""
        if self.pending_transfer:
            self.pending_transfer.confirmed = True
            req = self.pending_transfer
            self.pending_transfer = None
            logger.info(f"Confirmed file transfer: '{req.file_path}' -> {req.recipient}")
            return req
        return None

    def cancel_pending_transfer(self) -> str:
        """Cancel pending file transfer."""
        if self.pending_transfer:
            path = self.pending_transfer.file_path
            self.pending_transfer = None
            logger.info(f"Cancelled file transfer: '{path}'")
            return "File transfer cancelled."
        return "No pending file transfer to cancel."


# Global singleton instance
file_transfer_manager = FileTransferManager()
