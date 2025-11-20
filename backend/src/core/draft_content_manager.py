"""
Draft Content Manager

Manages partial blog drafts during generation with Redis-backed storage.
Drafts are stored as sections are generated and cleaned up on completion.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DraftContentManager:
    """
    Manages partial blog drafts during generation.
    
    Features:
    - Section-based content updates
    - Redis-backed storage
    - Automatic cleanup on completion
    - Progress tracking
    """
    
    def __init__(self, redis_manager):
        """
        Initialize draft content manager.
        
        Args:
            redis_manager: Redis manager instance for storage
        """
        self.redis = redis_manager
        self.draft_ttl = 3600  # 1 hour default TTL
        
        logger.info("📄 DraftContentManager initialized")
    
    async def update_draft(
        self,
        task_id: str,
        section: str,
        content: str,
        progress: Optional[int] = None
    ):
        """
        Update draft content for a specific section.
        
        Args:
            task_id: Task identifier
            section: Section name (e.g., 'title', 'introduction', 'section1')
            content: Section content
            progress: Optional progress percentage (0-100)
        """
        try:
            key = f"draft_content:{task_id}"
            
            # Get existing draft or create new one
            draft = await self.get_draft(task_id) or {
                "sections": {},
                "progress": 0
            }
            
            # Update section
            draft["sections"][section] = content
            draft["updated_at"] = datetime.utcnow().isoformat()
            
            if progress is not None:
                draft["progress"] = progress
            
            # Save to Redis
            await self.redis.redis_client.set(
                key,
                json.dumps(draft),
                ex=self.draft_ttl
            )
            
            logger.debug(
                f"📄 Draft updated for {task_id}: section={section}, "
                f"content_length={len(content)}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to update draft for {task_id}: {e}",
                exc_info=True
            )
    
    async def update_draft_bulk(
        self,
        task_id: str,
        sections: Dict[str, str],
        progress: Optional[int] = None
    ):
        """
        Update multiple sections at once.
        
        Args:
            task_id: Task identifier
            sections: Dictionary of section_name -> content
            progress: Optional progress percentage (0-100)
        """
        try:
            key = f"draft_content:{task_id}"
            
            # Get existing draft or create new one
            draft = await self.get_draft(task_id) or {
                "sections": {},
                "progress": 0
            }
            
            # Update all sections
            draft["sections"].update(sections)
            draft["updated_at"] = datetime.utcnow().isoformat()
            
            if progress is not None:
                draft["progress"] = progress
            
            # Save to Redis
            await self.redis.redis_client.set(
                key,
                json.dumps(draft),
                ex=self.draft_ttl
            )
            
            logger.debug(
                f"📄 Bulk draft update for {task_id}: "
                f"{len(sections)} sections updated"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to bulk update draft for {task_id}: {e}",
                exc_info=True
            )
    
    async def get_draft(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve current draft for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Draft dictionary with sections and metadata, or None if not found
        """
        try:
            key = f"draft_content:{task_id}"
            draft_json = await self.redis.redis_client.get(key)
            
            if not draft_json:
                return None
            
            # Redis returns bytes, decode if needed
            if isinstance(draft_json, bytes):
                draft_json = draft_json.decode('utf-8')
            
            draft = json.loads(draft_json)
            logger.debug(
                f"📖 Retrieved draft for {task_id}: "
                f"{len(draft.get('sections', {}))} sections"
            )
            
            return draft
            
        except Exception as e:
            logger.error(
                f"Failed to get draft for {task_id}: {e}",
                exc_info=True
            )
            return None
    
    async def get_draft_section(
        self,
        task_id: str,
        section: str
    ) -> Optional[str]:
        """
        Get a specific section from the draft.
        
        Args:
            task_id: Task identifier
            section: Section name
        
        Returns:
            Section content or None if not found
        """
        try:
            draft = await self.get_draft(task_id)
            if not draft:
                return None
            
            return draft.get("sections", {}).get(section)
            
        except Exception as e:
            logger.error(
                f"Failed to get draft section for {task_id}: {e}",
                exc_info=True
            )
            return None
    
    async def has_draft(self, task_id: str) -> bool:
        """
        Check if a draft exists for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if draft exists, False otherwise
        """
        try:
            key = f"draft_content:{task_id}"
            exists = await self.redis.redis_client.exists(key)
            return bool(exists)
            
        except Exception as e:
            logger.error(
                f"Failed to check draft existence for {task_id}: {e}",
                exc_info=True
            )
            return False
    
    async def get_draft_progress(self, task_id: str) -> int:
        """
        Get the progress percentage from the draft.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Progress percentage (0-100), or 0 if not found
        """
        try:
            draft = await self.get_draft(task_id)
            if not draft:
                return 0
            
            return draft.get("progress", 0)
            
        except Exception as e:
            logger.error(
                f"Failed to get draft progress for {task_id}: {e}",
                exc_info=True
            )
            return 0
    
    async def cleanup_draft(self, task_id: str):
        """
        Delete draft when blog generation completes.
        
        Args:
            task_id: Task identifier
        """
        try:
            key = f"draft_content:{task_id}"
            await self.redis.redis_client.delete(key)
            
            logger.info(f"🗑️ Draft deleted for {task_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup draft for {task_id}: {e}",
                exc_info=True
            )
    
    async def set_draft_metadata(
        self,
        task_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Set metadata for the draft (e.g., title, hero_image_url).
        
        Args:
            task_id: Task identifier
            metadata: Dictionary of metadata key-value pairs
        """
        try:
            key = f"draft_content:{task_id}"
            
            # Get existing draft or create new one
            draft = await self.get_draft(task_id) or {
                "sections": {},
                "progress": 0
            }
            
            # Update metadata
            for key_name, value in metadata.items():
                draft[key_name] = value
            
            draft["updated_at"] = datetime.utcnow().isoformat()
            
            # Save to Redis
            await self.redis.redis_client.set(
                key,
                json.dumps(draft),
                ex=self.draft_ttl
            )
            
            logger.debug(
                f"📄 Metadata updated for {task_id}: {list(metadata.keys())}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to set draft metadata for {task_id}: {e}",
                exc_info=True
            )
    
    async def get_section_count(self, task_id: str) -> int:
        """
        Get the number of sections in the draft.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Number of sections
        """
        try:
            draft = await self.get_draft(task_id)
            if not draft:
                return 0
            
            return len(draft.get("sections", {}))
            
        except Exception as e:
            logger.error(
                f"Failed to get section count for {task_id}: {e}",
                exc_info=True
            )
            return 0
    
    def configure(self, draft_ttl: Optional[int] = None):
        """
        Configure draft manager settings.
        
        Args:
            draft_ttl: Maximum TTL for drafts (seconds)
        """
        if draft_ttl is not None:
            self.draft_ttl = draft_ttl
            logger.info(f"📄 Draft TTL configured to {draft_ttl} seconds")


# Note: Global instance will be created in main.py after redis_manager is initialized
