"""
Cloudflare R2 Storage Service
Handles interview recording uploads to R2 (S3-compatible storage)
"""

import logging
import io
from typing import Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2StorageService:
    """
    Service for uploading/downloading interview recordings to Cloudflare R2
    """
    
    def __init__(self):
        """Initialize R2 client using boto3 (S3-compatible)"""
        if not all([
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_ENDPOINT,
            settings.R2_BUCKET_NAME
        ]):
            logger.error("❌ R2 credentials not fully configured")
            self.client = None
            self.bucket_name = None
            self.public_url = None
            return
        
        try:
            # Configure boto3 client for R2
            self.client = boto3.client(
                's3',
                endpoint_url=settings.R2_ENDPOINT,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name='auto',  # R2 uses 'auto' for region
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3}
                )
            )
            
            self.bucket_name = settings.R2_BUCKET_NAME
            self.public_url = settings.R2_PUBLIC_URL
            
            logger.info("✅ R2 Storage Service initialized")
            logger.info(f"   Bucket: {self.bucket_name}")
            logger.info(f"   Public URL: {self.public_url}")
            
        except Exception as e:
            logger.exception(f"❌ Failed to initialize R2: {e}")
            self.client = None
    
    def generate_recording_key(self, interview_id: str, file_type: str = "webm") -> str:
        """
        Generate a unique key for storing interview recording
        
        Args:
            interview_id: Interview ID
            file_type: File extension (webm, wav, mp3)
            
        Returns:
            S3 key path (e.g., "interviews/2024/12/interview_abc123_20241202.webm")
        """
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        
        return f"interviews/{date_path}/interview_{interview_id}_{timestamp}.{file_type}"
    
    async def upload_recording(
        self,
        interview_id: str,
        audio_data: bytes,
        file_type: str = "webm",
        metadata: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Upload interview recording to R2
        
        Args:
            interview_id: Interview ID
            audio_data: Raw audio bytes
            file_type: File extension
            metadata: Additional metadata to store
            
        Returns:
            Dict with upload info or None if failed
        """
        if not self.client:
            logger.error("R2 client not initialized")
            return None
        
        if not audio_data or len(audio_data) == 0:
            logger.warning("Empty audio data provided")
            return None
        
        try:
            # Generate unique key
            key = self.generate_recording_key(interview_id, file_type)
            
            # Prepare metadata
            s3_metadata = {
                'interview-id': interview_id,
                'upload-date': datetime.utcnow().isoformat(),
            }
            if metadata:
                for k, v in metadata.items():
                    s3_metadata[k] = str(v)
            
            # Determine content type
            content_type_map = {
                'webm': 'audio/webm',
                'wav': 'audio/wav',
                'mp3': 'audio/mpeg',
                'ogg': 'audio/ogg'
            }
            content_type = content_type_map.get(file_type, 'application/octet-stream')
            
            logger.info(f"📤 Uploading recording: {key} ({len(audio_data)} bytes)")
            
            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=audio_data,
                ContentType=content_type,
                Metadata=s3_metadata
            )
            
            # Generate public URL
            public_url = f"{self.public_url}/{key}" if self.public_url else None
            
            logger.info(f"✅ Recording uploaded successfully")
            logger.info(f"   Key: {key}")
            logger.info(f"   Size: {len(audio_data)} bytes")
            logger.info(f"   URL: {public_url}")
            
            return {
                'key': key,
                'bucket': self.bucket_name,
                'size': len(audio_data),
                'content_type': content_type,
                'public_url': public_url,
                'uploaded_at': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.exception(f"❌ R2 upload failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"❌ Upload error: {e}")
            return None
    
    async def download_recording(self, key: str) -> Optional[bytes]:
        """
        Download recording from R2
        
        Args:
            key: S3 object key
            
        Returns:
            Audio bytes or None if failed
        """
        if not self.client:
            logger.error("R2 client not initialized")
            return None
        
        try:
            logger.info(f"📥 Downloading recording: {key}")
            
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            audio_data = response['Body'].read()
            
            logger.info(f"✅ Downloaded {len(audio_data)} bytes")
            return audio_data
            
        except ClientError as e:
            logger.exception(f"❌ R2 download failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"❌ Download error: {e}")
            return None
    
    async def delete_recording(self, key: str) -> bool:
        """
        Delete recording from R2
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.error("R2 client not initialized")
            return False
        
        try:
            logger.info(f"🗑️ Deleting recording: {key}")
            
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"✅ Recording deleted")
            return True
            
        except ClientError as e:
            logger.exception(f"❌ R2 delete failed: {e}")
            return False
        except Exception as e:
            logger.exception(f"❌ Delete error: {e}")
            return False
    
    def get_public_url(self, key: str) -> Optional[str]:
        """
        Get public URL for a recording
        
        Args:
            key: S3 object key
            
        Returns:
            Public URL or None
        """
        if not self.public_url:
            logger.warning("R2_PUBLIC_URL not configured")
            return None
        
        return f"{self.public_url}/{key}"