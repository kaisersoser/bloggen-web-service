"""
Reference Deduplication Tool - Removes duplicate references and consolidates citations.

This tool analyzes blog content to identify duplicate references and consolidates
them into a clean, numbered reference list where each unique source appears only once.
"""

import re
import logging
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class Reference:
    """Represents a single reference with metadata"""
    url: str
    title: str
    description: str
    original_number: int
    first_appearance: int  # Position in text where first cited
    citation_count: int = 1


@dataclass
class DeduplicationReport:
    """Report of reference deduplication process"""
    total_references_found: int
    unique_references: int
    duplicates_removed: int
    references_consolidated: List[Reference]
    content_updated: bool


class ReferenceDeduplicator:
    """
    Deduplicates references in blog content and consolidates citations.
    
    This tool:
    1. Extracts all references from the References section
    2. Identifies duplicates based on URL and title similarity
    3. Consolidates duplicate references into single entries
    4. Updates inline citations to point to consolidated references
    5. Regenerates a clean, numbered reference list
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns for finding references and citations
        self.reference_section_pattern = r'### References\s*\n(.*?)(?=\n###|\n---|\Z)'
        self.reference_item_pattern = r'(\d+)\.\s*(.+?)\[([^\]]+)\]\(([^)]+)\)'
        self.inline_citation_pattern = r'\[(\d+)\]'
        
        # URL similarity threshold for considering references as duplicates
        self.url_similarity_threshold = 0.8
    
    def extract_references_section(self, content: str) -> Tuple[str, str]:
        """Extract the references section and return (section_content, remaining_content)"""
        match = re.search(self.reference_section_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not match:
            self.logger.warning("No References section found in content")
            return "", content
        
        references_section = match.group(1).strip()
        # Remove the references section from content
        content_without_refs = content[:match.start()] + content[match.end():]
        
        return references_section, content_without_refs
    
    def parse_references(self, references_section: str) -> List[Reference]:
        """Parse individual references from the references section"""
        references = []
        
        # Split by lines and process each reference
        lines = references_section.split('\n')
        current_ref_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new reference (starts with number)
            if re.match(r'^\d+\.', line):
                # Process previous reference if exists
                if current_ref_lines:
                    ref = self._parse_single_reference('\n'.join(current_ref_lines))
                    if ref:
                        references.append(ref)
                
                # Start new reference
                current_ref_lines = [line]
            else:
                # Continuation of current reference
                if current_ref_lines:
                    current_ref_lines.append(line)
        
        # Process final reference
        if current_ref_lines:
            ref = self._parse_single_reference('\n'.join(current_ref_lines))
            if ref:
                references.append(ref)
        
        return references
    
    def _parse_single_reference(self, ref_text: str) -> Optional[Reference]:
        """Parse a single reference entry"""
        # Try to extract number, title, and URL using various patterns
        patterns = [
            r'(\d+)\.\s*(.+?)\.\s*\[([^\]]+)\]\(([^)]+)\)',  # Standard format with period
            r'(\d+)\.\s*(.+?)\[([^\]]+)\]\(([^)]+)\)',       # Without period before link
            r'(\d+)\.\s*\*(.+?)\*\.\s*\[([^\]]+)\]\(([^)]+)\)',  # Italicized title
            r'(\d+)\.\s*(.+?)\s+\[([^\]]+)\]\(([^)]+)\)',    # Space before link
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref_text, re.DOTALL)
            if match:
                number = int(match.group(1))
                title = match.group(2).strip()
                link_text = match.group(3).strip()
                url = match.group(4).strip()
                
                # Create description from title and link text
                description = f"{title}. {link_text}" if title != link_text else title
                
                return Reference(
                    url=url,
                    title=title,
                    description=description,
                    original_number=number,
                    first_appearance=0  # Will be set later
                )
        
        self.logger.warning(f"Could not parse reference: {ref_text[:100]}...")
        return None
    
    def find_duplicates(self, references: List[Reference]) -> Dict[str, List[Reference]]:
        """Group references by similarity to identify duplicates"""
        duplicate_groups = {}
        processed = set()
        
        for i, ref in enumerate(references):
            if i in processed:
                continue
            
            # Create group for this reference
            group_key = self._normalize_url(ref.url)
            duplicate_groups[group_key] = [ref]
            processed.add(i)
            
            # Find similar references
            for j, other_ref in enumerate(references[i+1:], i+1):
                if j in processed:
                    continue
                
                if self._are_references_similar(ref, other_ref):
                    duplicate_groups[group_key].append(other_ref)
                    processed.add(j)
        
        # Only return groups that have duplicates
        return {k: v for k, v in duplicate_groups.items() if len(v) > 1}
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        try:
            parsed = urlparse(url)
            # Use domain + path as the key for grouping
            return f"{parsed.netloc.lower()}{parsed.path.lower()}"
        except:
            return url.lower()
    
    def _are_references_similar(self, ref1: Reference, ref2: Reference) -> bool:
        """Check if two references are similar enough to be considered duplicates"""
        # Check URL similarity
        url1_norm = self._normalize_url(ref1.url)
        url2_norm = self._normalize_url(ref2.url)
        
        if url1_norm == url2_norm:
            return True
        
        # Check title similarity for same domain
        try:
            domain1 = urlparse(ref1.url).netloc.lower()
            domain2 = urlparse(ref2.url).netloc.lower()
            
            if domain1 == domain2:
                # Same domain - check title similarity
                title1_words = set(ref1.title.lower().split())
                title2_words = set(ref2.title.lower().split())
                
                if title1_words and title2_words:
                    overlap = len(title1_words & title2_words)
                    total = len(title1_words | title2_words)
                    similarity = overlap / total if total > 0 else 0
                    
                    return similarity >= self.url_similarity_threshold
        except:
            pass
        
        return False
    
    def consolidate_duplicates(self, duplicate_groups: Dict[str, List[Reference]]) -> List[Reference]:
        """Consolidate duplicate references into single entries"""
        consolidated = []
        
        for group in duplicate_groups.values():
            # Use the first reference as the base
            primary_ref = group[0]
            
            # Count total citations
            total_citations = sum(ref.citation_count for ref in group)
            
            # Use the most comprehensive description
            best_description = max(group, key=lambda r: len(r.description)).description
            
            # Create consolidated reference
            consolidated_ref = Reference(
                url=primary_ref.url,
                title=primary_ref.title,
                description=best_description,
                original_number=primary_ref.original_number,
                first_appearance=primary_ref.first_appearance,
                citation_count=total_citations
            )
            
            consolidated.append(consolidated_ref)
        
        return consolidated
    
    def update_inline_citations(self, content: str, reference_mapping: Dict[int, int]) -> str:
        """Update inline citations to point to consolidated reference numbers"""
        def replace_citation(match):
            old_number = int(match.group(1))
            new_number = reference_mapping.get(old_number, old_number)
            return f"[{new_number}]"
        
        return re.sub(self.inline_citation_pattern, replace_citation, content)
    
    def generate_references_section(self, references: List[Reference]) -> str:
        """Generate a clean, deduplicated references section"""
        if not references:
            return ""
        
        lines = ["### References", ""]
        
        for i, ref in enumerate(references, 1):
            # Format reference entry
            ref_line = f"{i}. {ref.description} [{ref.url}]({ref.url})"
            lines.append(ref_line)
        
        return "\n".join(lines)
    
    def deduplicate_references(self, content: str) -> Tuple[str, DeduplicationReport]:
        """
        Main method to deduplicate references in blog content.
        
        Returns:
            Tuple of (deduplicated_content, deduplication_report)
        """
        self.logger.info("🔧 Starting reference deduplication process")
        
        # Extract references section
        references_section, content_without_refs = self.extract_references_section(content)
        
        if not references_section:
            report = DeduplicationReport(
                total_references_found=0,
                unique_references=0,
                duplicates_removed=0,
                references_consolidated=[],
                content_updated=False
            )
            return content, report
        
        # Parse references
        references = self.parse_references(references_section)
        self.logger.info(f"📊 Found {len(references)} total references")
        
        if len(references) <= 1:
            # No duplicates possible
            report = DeduplicationReport(
                total_references_found=len(references),
                unique_references=len(references),
                duplicates_removed=0,
                references_consolidated=references,
                content_updated=False
            )
            return content, report
        
        # Find duplicates
        duplicate_groups = self.find_duplicates(references)
        
        if not duplicate_groups:
            self.logger.info("✅ No duplicate references found")
            report = DeduplicationReport(
                total_references_found=len(references),
                unique_references=len(references),
                duplicates_removed=0,
                references_consolidated=references,
                content_updated=False
            )
            return content, report
        
        # Consolidate duplicates
        self.logger.info(f"🔍 Found {len(duplicate_groups)} groups of duplicate references")
        
        # Create list of unique references
        all_duplicated_refs = set()
        for group in duplicate_groups.values():
            for ref in group:
                all_duplicated_refs.add(ref.original_number)
        
        # Keep unique references and add consolidated ones
        unique_references = [ref for ref in references if ref.original_number not in all_duplicated_refs]
        consolidated_refs = self.consolidate_duplicates(duplicate_groups)
        
        # Combine and sort by original number
        final_references = unique_references + consolidated_refs
        final_references.sort(key=lambda r: r.original_number)
        
        # Create mapping for updating citations
        reference_mapping = {}
        for new_num, ref in enumerate(final_references, 1):
            # Map original number to new number
            reference_mapping[ref.original_number] = new_num
            
            # Also map other numbers in the same duplicate group
            for group in duplicate_groups.values():
                if any(r.original_number == ref.original_number for r in group):
                    for group_ref in group:
                        reference_mapping[group_ref.original_number] = new_num
        
        # Update inline citations
        updated_content = self.update_inline_citations(content_without_refs, reference_mapping)
        
        # Generate new references section
        new_references_section = self.generate_references_section(final_references)
        
        # Combine content
        final_content = updated_content.rstrip() + "\n\n" + new_references_section
        
        # Generate report
        duplicates_removed = len(references) - len(final_references)
        
        self.logger.info(f"✅ Deduplication complete: {duplicates_removed} duplicates removed")
        
        report = DeduplicationReport(
            total_references_found=len(references),
            unique_references=len(final_references),
            duplicates_removed=duplicates_removed,
            references_consolidated=final_references,
            content_updated=True
        )
        
        return final_content, report


def create_reference_deduplicator() -> ReferenceDeduplicator:
    """Factory function to create ReferenceDeduplicator instance"""
    return ReferenceDeduplicator()


def format_deduplication_report(report: DeduplicationReport) -> str:
    """Format deduplication report for logging/display"""
    lines = [
        "🔧 REFERENCE DEDUPLICATION REPORT",
        "=" * 50,
        f"📊 Total References Found: {report.total_references_found}",
        f"✅ Unique References: {report.unique_references}",
        f"🗑️ Duplicates Removed: {report.duplicates_removed}",
        f"📝 Content Updated: {'Yes' if report.content_updated else 'No'}",
        ""
    ]
    
    if report.references_consolidated:
        lines.append("🔍 Final Reference List:")
        for i, ref in enumerate(report.references_consolidated, 1):
            lines.append(f"{i:2d}. {ref.title[:60]}{'...' if len(ref.title) > 60 else ''}")
            lines.append(f"    🔗 {ref.url}")
    
    return "\n".join(lines)