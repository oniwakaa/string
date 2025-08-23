"""
Memory Adapters for Agent-MemOS Integration

Provides minimal, surgical transformation utilities for converting agent outputs
into MemOS-compatible memory items. Follows established MemOS patterns exactly.

Author: Enhanced WebResearcher Integration
Date: 2025-08-20
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

# Import MemOS types using the same pattern as other modules
try:
    from string_ai_coding_assistant.memos.memories.textual.item import TextualMemoryItem, TextualMemoryMetadata
    MEMOS_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"MemOS not available: {e}")
    MEMOS_AVAILABLE = False

logger = logging.getLogger(__name__)


class WebResearchMemoryAdapter:
    """
    Minimal adapter for transforming WebResearchAgent outputs into MemOS TextualMemoryItem format.
    
    Follows established MemOS patterns for metadata structure and content organization.
    """
    
    @staticmethod
    def create_memory_item(
        research_result: Dict[str, Any],
        user_id: str,
        session_id: Optional[str] = None
    ) -> Optional["TextualMemoryItem"]:
        """
        Transform WebResearch result into TextualMemoryItem.
        
        Args:
            research_result: Output from WebResearchAgent.execute()
            user_id: User ID for memory ownership
            session_id: Optional session ID for context
            
        Returns:
            TextualMemoryItem or None if MemOS unavailable or invalid input
            
        Transformation mapping (WebResearch → MemOS):
        - research_summary → memory (main content)
        - source_title → entities[0] (primary entity)
        - source_domain → tags[0] (categorization tag)
        - query → background (context for memory)
        - citation → sources[0] (attribution)
        """
        if not MEMOS_AVAILABLE:
            logger.warning("MemOS not available - skipping memory creation")
            return None
            
        if not research_result or 'research_summary' not in research_result:
            logger.warning("Invalid research result - missing research_summary")
            return None
        
        try:
            # Extract core content
            summary = research_result.get('research_summary', '')
            source_title = research_result.get('source_title', 'Web Research')
            source_domain = research_result.get('source_domain', 'unknown')
            query = research_result.get('query', '')
            citation = research_result.get('citation', '')
            
            # Generate namespaced deterministic UUID for idempotent writes with collision prevention
            # Hash: "web:" prefix + normalized content + domain + URL + date bucket
            import uuid
            date_bucket = datetime.now().strftime("%Y-%m-%d")
            source_url = research_result.get('raw_extracted_content', {}).get('url', 'unknown_url')
            
            # Namespace with "web:" prefix to prevent codebase collisions
            namespace_content = f"web:{summary[:200]}{source_domain}{source_url}{date_bucket}".encode()
            hash_digest = hashlib.sha256(namespace_content).digest()[:16]
            memory_id = str(uuid.UUID(bytes=hash_digest))
            
            # Create metadata following established MemOS patterns with enhanced partitioning
            metadata = TextualMemoryMetadata(
                user_id=user_id,
                session_id=session_id,
                source="web",  # Authoritative source type for web content
                type="fact",   # Use valid enum value - web research extracts factual information
                memory_time=date_bucket,  # YYYY-MM-DD format as required
                confidence=85.0,  # High confidence for direct web retrieval
                entities=[source_title] if source_title != 'Web Research' else [],
                tags=[source_domain, "web_research", "scraped_content"],  # Enhanced categorization
                visibility="session",  # Session-scoped visibility
                updated_at=datetime.now().isoformat()
            )
            
            # Create structured memory content with citation and source URL for indexing
            content_parts = [summary]
            if citation:
                content_parts.append(f"[Retrieved from: {citation}]")
            if source_url and source_url != 'unknown_url':
                content_parts.append(f"[Source URL: {source_url}]")
            
            memory_content = "\n\n".join(content_parts)
            
            # Create TextualMemoryItem using established pattern
            memory_item = TextualMemoryItem(
                id=memory_id,
                memory=memory_content,
                metadata=metadata
            )
            
            logger.info(f"✅ Created memory item: {memory_id[:8]}... for domain {source_domain}, "
                       f"source=web, type=fact, tags={metadata.tags}")
            return memory_item
            
        except Exception as e:
            logger.error(f"❌ Failed to create memory item: {e}")
            return None
    
    @staticmethod 
    def validate_memory_item(memory_item: "TextualMemoryItem") -> bool:
        """
        Validate memory item against MemOS schema requirements.
        
        Args:
            memory_item: TextualMemoryItem to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not MEMOS_AVAILABLE or not memory_item:
            return False
            
        try:
            # Validate required fields
            if not memory_item.memory or not memory_item.metadata:
                return False
                
            # Validate metadata constraints
            metadata = memory_item.metadata
            if metadata.confidence and (metadata.confidence < 0 or metadata.confidence > 100):
                return False
                
            # Validate memory_time format if present
            if metadata.memory_time:
                datetime.strptime(metadata.memory_time, "%Y-%m-%d")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Memory item validation failed: {e}")
            return False