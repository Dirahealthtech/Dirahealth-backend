from pydantic import BaseModel, model_validator, field_validator
from typing import List, Optional
from datetime import datetime
import bleach

from .product import ProductResponse


# Try to import CSS sanitizer if available
try:
    from bleach.css_sanitizer import CSSSanitizer
    CSS_SANITIZER = CSSSanitizer(allowed_css_properties=[
        # Text styling
        'color', 'background-color', 'font-size', 'font-weight', 'font-style',
        'font-family', 'text-align', 'text-decoration', 'text-transform',
        'line-height', 'letter-spacing', 'word-spacing',
        
        # Layout and spacing
        'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
        'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
        'width', 'height', 'max-width', 'max-height', 'min-width', 'min-height',
        
        # Border and display
        'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
        'border-color', 'border-style', 'border-width', 'border-radius',
        'display', 'visibility', 'opacity',
        
        # Positioning (limited for security)
        'position', 'top', 'right', 'bottom', 'left', 'z-index',
        
        # Flexbox and grid (common in modern layouts)
        'flex', 'flex-direction', 'flex-wrap', 'justify-content', 'align-items',
        'align-content', 'align-self', 'flex-grow', 'flex-shrink', 'flex-basis',
        
        # Other useful properties
        'vertical-align', 'white-space', 'overflow', 'overflow-x', 'overflow-y',
        'cursor', 'list-style', 'list-style-type', 'text-indent'
    ])
except ImportError:
    CSS_SANITIZER = None


# Simplified schemas for public API
class SimplifiedProductResponse(BaseModel):
    id: int
    slug: str
    name: str
    price: float
    discounted_price: Optional[float] = None
    images: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def extract_pricing_fields(cls, data):
        """Extract price and discounted_price from nested pricing structure"""
        if hasattr(data, '__dict__'):
            data_dict = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    data_dict[key] = value
            data = data_dict
        
        if isinstance(data, dict):
            # If pricing is nested, extract it
            if 'pricing' in data and isinstance(data['pricing'], dict):
                data['price'] = data['pricing'].get('price', 0.0)
                data['discounted_price'] = data['pricing'].get('discounted_price', 0.0)
            elif hasattr(data.get('pricing'), 'price'):
                # Handle case where pricing is a Pydantic object
                pricing = data['pricing']
                data['price'] = pricing.price
                data['discounted_price'] = pricing.discounted_price
        
        return data

    class Config:
        from_attributes = True


class SimplifiedHomepageSectionResponse(BaseModel):
    title: str
    display_order: int
    is_active: bool
    id: int
    products: List[SimplifiedProductResponse] = []

    class Config:
        from_attributes = True


# Original detailed schemas
class HomepageSectionBase(BaseModel):
    title: str
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True

    @field_validator('description', mode='before')
    @classmethod
    def sanitize_html_description(cls, v):
        """Sanitize HTML description from rich text editor using bleach"""
        if not v:
            return v
        
        # Define allowed HTML tags for rich text content
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'span',
            'div', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
            'tfoot', 'caption', 'sub', 'sup', 'small', 'mark', 'del', 'ins'
        ]
        
        # Define allowed attributes for specific tags
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'style'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
            'p': ['style'],
            'span': ['style'],
            'div': ['style'],
            'h1': ['style'], 'h2': ['style'], 'h3': ['style'], 
            'h4': ['style'], 'h5': ['style'], 'h6': ['style'],
            'strong': ['style'], 'b': ['style'], 'em': ['style'], 'i': ['style'], 'u': ['style'],
            'ul': ['style'], 'ol': ['style'], 'li': ['style'],
            'blockquote': ['style'],
            'table': ['style', 'border', 'cellpadding', 'cellspacing'],
            'tr': ['style'],
            'td': ['style', 'colspan', 'rowspan'],
            'th': ['style', 'colspan', 'rowspan'],
            'thead': ['style'], 'tbody': ['style'], 'tfoot': ['style'],
            'caption': ['style'],
            'sub': ['style'], 'sup': ['style'],
            'small': ['style'], 'mark': ['style'], 'del': ['style'], 'ins': ['style'],
            '*': ['class']  # Allow class attribute on all tags
        }
        
        # Define allowed protocols for links
        allowed_protocols = ['http', 'https', 'mailto']
        
        # Sanitize the HTML using bleach with enhanced security
        sanitized = bleach.clean(
            v,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True,  # Remove disallowed tags entirely
            strip_comments=True,  # Remove HTML comments
            css_sanitizer=CSS_SANITIZER  # CSS sanitization if available
        )
        
        return sanitized


class HomepageSectionCreate(HomepageSectionBase):
    product_ids: Optional[List[int]] = []


class HomepageSectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    product_ids: Optional[List[int]] = None

    @field_validator('description', mode='before')
    @classmethod
    def sanitize_html_description(cls, v):
        """Sanitize HTML description from rich text editor using bleach"""
        if not v:
            return v
        
        # Define allowed HTML tags for rich text content
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'span',
            'div', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
            'tfoot', 'caption', 'sub', 'sup', 'small', 'mark', 'del', 'ins'
        ]
        
        # Define allowed attributes for specific tags
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'style'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
            'p': ['style'],
            'span': ['style'],
            'div': ['style'],
            'h1': ['style'], 'h2': ['style'], 'h3': ['style'], 
            'h4': ['style'], 'h5': ['style'], 'h6': ['style'],
            'strong': ['style'], 'b': ['style'], 'em': ['style'], 'i': ['style'], 'u': ['style'],
            'ul': ['style'], 'ol': ['style'], 'li': ['style'],
            'blockquote': ['style'],
            'table': ['style', 'border', 'cellpadding', 'cellspacing'],
            'tr': ['style'],
            'td': ['style', 'colspan', 'rowspan'],
            'th': ['style', 'colspan', 'rowspan'],
            'thead': ['style'], 'tbody': ['style'], 'tfoot': ['style'],
            'caption': ['style'],
            'sub': ['style'], 'sup': ['style'],
            'small': ['style'], 'mark': ['style'], 'del': ['style'], 'ins': ['style'],
            '*': ['class']  # Allow class attribute on all tags
        }
        
        # Define allowed protocols for links
        allowed_protocols = ['http', 'https', 'mailto']
        
        # Sanitize the HTML using bleach with enhanced security
        sanitized = bleach.clean(
            v,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True,  # Remove disallowed tags entirely
            strip_comments=True,  # Remove HTML comments
            css_sanitizer=CSS_SANITIZER  # CSS sanitization if available
        )
        
        return sanitized


class HomepageSectionResponse(HomepageSectionBase):
    id: int
    is_active: bool
    slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    products: List[ProductResponse] = []

    @model_validator(mode='before')
    @classmethod
    def generate_slug_if_missing(cls, data):
        """Generate slug from title if slug is None"""
        if hasattr(data, '__dict__'):
            # Convert SQLAlchemy object to dict
            data_dict = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    data_dict[key] = value
            data = data_dict
        
        if isinstance(data, dict) and (data.get('slug') is None):
            title = data.get('title', '')
            if title:
                # Generate slug from title
                import re
                slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
                slug = re.sub(r'\s+', '-', slug).strip('-')
                data['slug'] = slug or 'homepage-section'
        
        return data

    class Config:
        from_attributes = True


class HomepageSectionListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    display_order: int
    is_active: bool
    product_count: int
    created_at: datetime


    @field_validator('description', mode='before')
    @classmethod
    def sanitize_html_description(cls, v):
        """Sanitize HTML description from rich text editor using bleach"""
        if not v:
            return v
        
        # Define allowed HTML tags for rich text content
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'span',
            'div', 'a', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
            'tfoot', 'caption', 'sub', 'sup', 'small', 'mark', 'del', 'ins'
        ]
        
        # Define allowed attributes for specific tags
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'style'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
            'p': ['style'],
            'span': ['style'],
            'div': ['style'],
            'h1': ['style'], 'h2': ['style'], 'h3': ['style'], 
            'h4': ['style'], 'h5': ['style'], 'h6': ['style'],
            'strong': ['style'], 'b': ['style'], 'em': ['style'], 'i': ['style'], 'u': ['style'],
            'ul': ['style'], 'ol': ['style'], 'li': ['style'],
            'blockquote': ['style'],
            'table': ['style', 'border', 'cellpadding', 'cellspacing'],
            'tr': ['style'],
            'td': ['style', 'colspan', 'rowspan'],
            'th': ['style', 'colspan', 'rowspan'],
            'thead': ['style'], 'tbody': ['style'], 'tfoot': ['style'],
            'caption': ['style'],
            'sub': ['style'], 'sup': ['style'],
            'small': ['style'], 'mark': ['style'], 'del': ['style'], 'ins': ['style'],
            '*': ['class']  # Allow class attribute on all tags
        }
        
        # Define allowed protocols for links
        allowed_protocols = ['http', 'https', 'mailto']
        
        # Sanitize the HTML using bleach with enhanced security
        sanitized = bleach.clean(
            v,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True,  # Remove disallowed tags entirely
            strip_comments=True,  # Remove HTML comments
            css_sanitizer=CSS_SANITIZER  # CSS sanitization if available
        )
        
        return sanitized

    class Config:
        from_attributes = True
