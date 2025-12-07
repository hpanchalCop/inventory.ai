"""AWS S3 service for storing images and metadata."""
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import io
from PIL import Image

from shared.config import settings


class S3Service:
    """Service for interacting with AWS S3."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        self._init_client()
    
    def _init_client(self):
        """Initialize S3 client."""
        try:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
            else:
                # Use default credentials (IAM role, environment, etc.)
                self.s3_client = boto3.client('s3', region_name=settings.aws_region)
            
            print("S3 client initialized")
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
    
    def upload_image(
        self, 
        image: Image.Image, 
        key: str, 
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Upload image to S3.
        
        Args:
            image: PIL Image object
            key: S3 key (path) for the image
            content_type: Image content type
            
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client:
            print("S3 client not initialized")
            return None
        
        try:
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                img_byte_arr,
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
            return url
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return None
    
    def download_image(self, key: str) -> Optional[Image.Image]:
        """
        Download image from S3.
        
        Args:
            key: S3 key (path) for the image
            
        Returns:
            PIL Image or None if failed
        """
        if not self.s3_client:
            print("S3 client not initialized")
            return None
        
        try:
            img_byte_arr = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, key, img_byte_arr)
            img_byte_arr.seek(0)
            
            image = Image.open(img_byte_arr)
            return image
        except ClientError as e:
            print(f"Error downloading from S3: {e}")
            return None
    
    def delete_image(self, key: str) -> bool:
        """
        Delete image from S3.
        
        Args:
            key: S3 key (path) for the image
            
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            print("S3 client not initialized")
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for temporary access.
        
        Args:
            key: S3 key (path) for the image
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if failed
        """
        if not self.s3_client:
            print("S3 client not initialized")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None


# Singleton instance
s3_service = S3Service()
