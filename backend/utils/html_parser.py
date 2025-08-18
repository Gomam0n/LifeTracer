# -*- coding: utf-8 -*-
"""
Simplified HTML parsing utilities
"""
from bs4 import BeautifulSoup
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class HTMLParser:
    """Simplified HTML parser for Wikipedia content"""
    
    @staticmethod
    def extract_section_by_id(html_content: str, section_id: str) -> str:
        """
        Extract content of a section by h2 id until the next h2 section
        
        Args:
            html_content: HTML content string
            section_id: Target h2 tag id (e.g., "生平")
        
        Returns:
            Extracted section text, empty string if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return HTMLParser._extract_section_content(soup, section_id)
        except Exception as e:
            logger.warning(f"Failed to extract section '{section_id}': {str(e)}")
            return ""
    
    @staticmethod
    def _extract_section_content(soup: BeautifulSoup, section_id: str) -> str:
        """Internal method to extract section content"""
        # Find target h2 tag
        target_h2 = soup.find('h2', {'id': section_id})
        if not target_h2:
            logger.debug(f"Section '{section_id}' not found")
            return ""
        
        logger.debug(f"Found section: {target_h2.get_text()}")
        
        # Find starting point for content extraction
        start_element = HTMLParser._find_content_start(target_h2)
        if not start_element:
            return ""
        
        # Extract content until next h2
        content_parts = []
        current = start_element
        
        while current:
            if HTMLParser._is_section_boundary(current):
                break
            
            if HTMLParser._is_content_element(current):
                text = HTMLParser._extract_clean_text(current)
                if text:
                    content_parts.append(text)
            
            current = current.next_sibling
        
        result = "\n\n".join(content_parts).strip()
        logger.debug(f"Extracted {len(result)} characters from section '{section_id}'")
        return result
    
    @staticmethod
    def _find_content_start(h2_element):
        """Find the starting element for content extraction"""
        # Try h2's parent container first, then h2 itself
        container = h2_element.parent
        return container.next_sibling if container else h2_element.next_sibling
    
    @staticmethod
    def _is_section_boundary(element) -> bool:
        """Check if element marks the start of a new section"""
        if not element or not hasattr(element, 'name'):
            return False
        
        # Direct h2 tag
        if element.name == 'h2':
            return True
        
        # Div containing h2 tag
        if element.name == 'div' and element.find('h2'):
            return True
        
        return False
    
    @staticmethod
    def _is_content_element(element) -> bool:
        """Check if element contains relevant content"""
        if not element or not hasattr(element, 'name'):
            return False
        
        # Skip non-content elements
        if element.name in ['script', 'style', 'meta', 'link']:
            return False
        
        # Include content elements
        if element.name in ['p', 'div', 'ul', 'ol', 'li', 'table', 'blockquote']:
            # Skip divs that contain h2 (section headers)
            if element.name == 'div' and element.find('h2'):
                return False
            return True
        
        return False
    
    @staticmethod
    def _extract_clean_text(element) -> str:
        """Extract clean text from element"""
        try:
            text = element.get_text(strip=True)
            # Filter out very short or empty text
            return text if text and len(text) > 5 else ""
        except Exception:
            return ""
    
    @staticmethod
    def extract_all_text(html_content: str) -> str:
        """
        Fallback method to extract all readable text from HTML
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract all text: {str(e)}")
            return ""