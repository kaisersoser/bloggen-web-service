"""
AWS S3 Image Storage Service for Blog Hero Images

This service handles:
- Downloading images from OpenAI DALL-E temporary URLs
- Converting to JPEG format for compression
- Uploading to permanent S3 storage
- Generating permanent public URLs
"""

import os
import boto3
import requests
import logging
from io import BytesIO
from PIL import Image
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class S3ImageStorage:
    """Service for storing images permanently in AWS S3"""

    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        self.region = os.getenv("AWS_S3_REGION", "us-east-1")

        if not all([self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError(
                "Missing AWS S3 configuration. Please check your .env file."
            )

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

        logger.info(f"S3ImageStorage initialized for bucket: {self.bucket_name}")

    def download_and_convert_image(self, image_url: str, quality: int = 85) -> BytesIO:
        """
        Download image from URL and convert to compressed JPEG format

        Args:
            image_url: URL of the image to download
            quality: JPEG compression quality (1-100, higher = better quality)

        Returns:
            BytesIO: Compressed JPEG image data
        """
        try:
            # Download the image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Open with PIL and convert to RGB (required for JPEG)
            image = Image.open(BytesIO(response.content))
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            # Resize if too large (max 1024x1024 to save storage costs)
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {image.size}")

            # Convert to JPEG with compression
            jpeg_buffer = BytesIO()
            image.save(jpeg_buffer, format="JPEG", quality=quality, optimize=True)
            jpeg_buffer.seek(0)

            logger.info(
                f"Converted image to JPEG (quality={quality}), size: {len(jpeg_buffer.getvalue())} bytes"
            )
            return jpeg_buffer

        except Exception as e:
            logger.error(f"Failed to download/convert image from {image_url}: {e}")
            raise

    def upload_image_to_s3(self, image_data: BytesIO, file_name: str) -> str:
        """
        Upload image data to S3 and return public URL

        Args:
            image_data: Image data as BytesIO
            file_name: Name for the file in S3

        Returns:
            str: Public URL of the uploaded image
        """
        try:
            # Upload to S3 without ACL (bucket should be configured for public read via bucket policy)
            self.s3_client.upload_fileobj(
                image_data,
                self.bucket_name,
                file_name,
                ExtraArgs={
                    "ContentType": "image/jpeg"
                    # Removed ACL since bucket doesn't support it
                },
            )

            # Generate public URL
            public_url = (
                f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_name}"
            )
            logger.info(f"Image uploaded successfully: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload image to S3: {e}")
            raise

    def store_hero_image(self, openai_image_url: str, blog_id: str) -> str:
        """
        Complete workflow: Download OpenAI image, convert to JPEG, upload to S3

        Args:
            openai_image_url: Temporary OpenAI DALL-E image URL
            blog_id: Unique blog identifier for file naming

        Returns:
            str: Permanent S3 public URL
        """
        try:
            logger.info(f"Starting hero image storage for blog {blog_id}")

            # Generate unique filename
            file_name = f"hero-images/{blog_id}-{uuid4().hex[:8]}.jpg"

            # Download and convert image
            jpeg_data = self.download_and_convert_image(openai_image_url)

            # Upload to S3
            permanent_url = self.upload_image_to_s3(jpeg_data, file_name)

            logger.info(f"Hero image stored successfully: {permanent_url}")
            return permanent_url

        except Exception as e:
            logger.error(f"Failed to store hero image for blog {blog_id}: {e}")
            raise

    def test_connection(self) -> bool:
        """Test S3 connection and bucket access"""
        try:
            # Try to list objects in bucket (will fail if no access)
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 connection test successful for bucket: {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"S3 connection test failed: {e}")
            return False

    def list_blog_images(self, blog_id: str) -> list[str]:
        """
        List all S3 objects/images associated with a specific blog ID

        Args:
            blog_id: The blog identifier to search for

        Returns:
            list[str]: List of S3 object keys for this blog
        """
        try:
            image_keys = []

            # List objects with blog_id prefix in hero-images/ folder
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket_name, Prefix=f"hero-images/{blog_id}-"
            )

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        image_keys.append(obj["Key"])

            logger.info(f"Found {len(image_keys)} S3 images for blog {blog_id}")
            return image_keys

        except Exception as e:
            logger.error(f"Failed to list images for blog {blog_id}: {e}")
            return []

    def extract_image_urls_from_content(self, content: str) -> list[str]:
        """
        Extract S3 image URLs from blog content using regex

        Args:
            content: Blog content that may contain S3 image URLs

        Returns:
            list[str]: List of S3 URLs found in content
        """
        import re

        # Pattern to match our S3 bucket URLs - handle None bucket_name/region
        bucket_name = self.bucket_name or ""
        region = self.region or "us-east-1"
        s3_pattern = rf"https://{re.escape(bucket_name)}\.s3\.{re.escape(region)}\.amazonaws\.com/[^\s\)\"']+"

        urls = re.findall(s3_pattern, content or "")

        logger.info(f"Extracted {len(urls)} S3 URLs from content")
        return urls

    def delete_image_by_url(self, s3_url: str) -> bool:
        """
        Delete a single S3 image by its public URL

        Args:
            s3_url: Full S3 public URL to delete

        Returns:
            bool: True if deletion succeeded, False otherwise
        """
        try:
            # Extract object key from URL
            # URL format: https://bucket.s3.region.amazonaws.com/key
            url_parts = s3_url.split(
                f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/", 1
            )
            if len(url_parts) != 2:
                logger.error(f"Invalid S3 URL format: {s3_url}")
                return False

            object_key = url_parts[1]

            # Delete the object
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)

            logger.info(f"Successfully deleted S3 object: {object_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete S3 object from URL {s3_url}: {e}")
            return False

    def delete_blog_images(
        self,
        blog_id: str,
        content: str | None = None,
        hero_image_url: str | None = None,
    ) -> tuple[int, list[str]]:
        """
        Delete all S3 images associated with a blog (hero + content images)

        Args:
            blog_id: Blog identifier
            content: Blog content to scan for S3 URLs (optional)
            hero_image_url: Hero image URL to delete (optional)

        Returns:
            tuple[int, list[str]]: (successful_deletions, failed_urls)
        """
        try:
            all_urls = set()
            bucket_name = self.bucket_name or ""

            # Add hero image URL if provided
            if hero_image_url and bucket_name in hero_image_url:
                all_urls.add(hero_image_url)

            # Extract S3 URLs from content
            if content:
                content_urls = self.extract_image_urls_from_content(content)
                all_urls.update(content_urls)

            # Get images by blog_id prefix
            blog_image_keys = self.list_blog_images(blog_id)
            for key in blog_image_keys:
                s3_url = (
                    f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                )
                all_urls.add(s3_url)

            if not all_urls:
                logger.info(f"No S3 images found for blog {blog_id}")
                return 0, []

            # Batch delete for efficiency
            successful_deletions = 0
            failed_urls = []

            # Convert URLs to object keys for batch deletion
            delete_objects = []
            for url in all_urls:
                try:
                    url_parts = url.split(
                        f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/", 1
                    )
                    if len(url_parts) == 2:
                        delete_objects.append({"Key": url_parts[1]})
                except Exception as e:
                    logger.error(f"Failed to parse S3 URL {url}: {e}")
                    failed_urls.append(url)

            # Perform batch deletion (max 1000 objects per batch)
            if delete_objects:
                batch_size = 1000
                for i in range(0, len(delete_objects), batch_size):
                    batch = delete_objects[i:i + batch_size]

                    try:
                        response = self.s3_client.delete_objects(
                            Bucket=self.bucket_name, Delete={"Objects": batch}
                        )

                        # Count successful deletions
                        if "Deleted" in response:
                            successful_deletions += len(response["Deleted"])

                        # Track any errors
                        if "Errors" in response:
                            for error in response["Errors"]:
                                failed_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{error['Key']}"
                                failed_urls.append(failed_url)
                                logger.error(
                                    f"S3 batch delete error for {error['Key']}: {error['Message']}"
                                )

                    except Exception as e:
                        logger.error(f"S3 batch delete failed: {e}")
                        # Add all URLs in this batch to failed list
                        for obj in batch:
                            failed_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{obj['Key']}"
                            failed_urls.append(failed_url)

            logger.info(
                f"Blog {blog_id} S3 cleanup: {successful_deletions} deleted, {len(failed_urls)} failed"
            )
            return successful_deletions, failed_urls

        except Exception as e:
            logger.error(f"Failed to delete images for blog {blog_id}: {e}")
            return 0, list(all_urls) if "all_urls" in locals() else []


# Global instance
s3_storage = None


def get_s3_storage() -> S3ImageStorage:
    """Get or create S3 storage instance"""
    global s3_storage
    if s3_storage is None:
        s3_storage = S3ImageStorage()
    return s3_storage
