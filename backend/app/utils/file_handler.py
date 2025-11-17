import os
import asyncio
import aiofiles
import logging
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

# ✅ Configure module logger
logger = logging.getLogger(__name__)


class FileHandler:
    """Handle file operations (upload, validation, delete)"""

    @staticmethod
    def validate_file_type(file: UploadFile) -> bool:
        """Validate that the uploaded file is a PDF"""
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = settings.ALLOWED_EXTENSIONS.split(',')

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only {', '.join(allowed_extensions)} files are allowed"
            )

        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MIME type. Only PDF files are allowed"
            )

        logger.info(f"✅ File type validated: {file.filename}")
        return True

    @staticmethod
    async def save_upload_file(file: UploadFile, user_id: str) -> tuple[str, int]:
        """
        Save uploaded file to user-specific directory.

        Returns:
            Tuple[str, int]: (file_path, file_size)
        """
        user_dir = Path(settings.UPLOAD_DIR) / "resumes" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"resume_{timestamp}{file_ext}"
        file_path = user_dir / safe_filename

        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE:
                    await asyncio.to_thread(os.remove, file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Max allowed: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB"
                    )
                await f.write(chunk)

        logger.info(f"💾 File saved: {file_path} ({file_size} bytes)")
        return str(file_path), file_size

    @staticmethod
    async def delete_file(file_path: str) -> bool:
        """Asynchronously delete a file if it exists."""
        try:
            if os.path.exists(file_path):
                await asyncio.to_thread(os.remove, file_path)  # ✅ Correct async-safe deletion
                logger.info(f"🗑️ File deleted: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
            return False
