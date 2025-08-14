from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import bleach

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

# Sub-schemas for nested structures
class PricingSchema(BaseModel):
    price: float
    discounted_price: Optional[float] = 0.0
    tax_rate: Optional[float] = 0.0

class InventorySchema(BaseModel):
    sku: str
    stock: int
    reorder_level: Optional[int] = None
    requires_prescription: bool = False
    is_active: bool = True
    supports_online_payment: bool = True
    supports_cod: bool = True

class InventoryUpdateSchema(BaseModel):
    sku: Optional[str] = None
    stock: Optional[int] = None
    reorder_level: Optional[int] = None
    requires_prescription: Optional[bool] = None
    is_active: Optional[bool] = None
    supports_online_payment: Optional[bool] = None
    supports_cod: Optional[bool] = None

class DimensionsSchema(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    unit: str = "cm"

class ShippingSchema(BaseModel):
    weight: Optional[float] = None
    weight_unit: str = "kg"
    dimensions: Optional[DimensionsSchema] = None

class WarrantySchema(BaseModel):
    period: Optional[int] = None
    unit: Optional[str] = None
    description: Optional[str] = None

class MetadataSchema(BaseModel):
    tags: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None

# Simplified schema for homepage/activity endpoints
class SimpleProductResponse(BaseModel):
    id: int
    slug: str
    name: str
    category_id: int
    pricing: PricingSchema
    images: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def map_flat_to_nested(cls, data):
        """Map flat database fields to nested schema structure"""
        # Handle None data
        if data is None:
            raise ValueError("Product data cannot be None")
        
        # Convert SQLAlchemy model to dict if needed
        if hasattr(data, '__dict__'):
            data_dict = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    data_dict[key] = value
            data = data_dict
        
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict or SQLAlchemy model, got {type(data)}")
        
        # Map pricing fields
        data['pricing'] = {
            'price': data.get('price', 0.0),
            'discounted_price': data.get('discounted_price', 0.0)
        }
        
        return data

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    description: str  # Rich HTML content from TinyMCE/WYSIWYG
    category_id: int
    supplier_id: Optional[int] = None
    pricing: PricingSchema
    inventory: InventorySchema
    images: Optional[str] = None
    shipping: Optional[ShippingSchema] = None
    warranty: Optional[WarrantySchema] = None
    metadata: Optional[MetadataSchema] = None

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

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    pricing: Optional[PricingSchema] = None
    inventory: Optional[InventoryUpdateSchema] = None
    images: Optional[str] = None
    shipping: Optional[ShippingSchema] = None
    warranty: Optional[WarrantySchema] = None
    metadata: Optional[MetadataSchema] = None

    @field_validator('supplier_id', mode='before')
    @classmethod
    def validate_supplier_id(cls, v):
        """Convert supplier_id of 0 to None (no supplier)"""
        if v == 0:
            return None
        return v

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
            '*': ['class']
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

class ProductResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str  # Sanitized rich HTML
    category_id: int
    supplier_id: Optional[int] = None
    pricing: PricingSchema
    inventory: InventorySchema
    images: Optional[str] = None
    shipping: Optional[ShippingSchema] = None
    warranty: Optional[WarrantySchema] = None
    metadata: Optional[MetadataSchema] = None
    created_at: datetime
    updated_at: datetime
    
    @model_validator(mode='before')
    @classmethod
    def map_flat_to_nested(cls, data):
        """Map flat database fields to nested schema structure"""
        # Handle None data
        if data is None:
            raise ValueError("Product data cannot be None")
        
        # Convert SQLAlchemy model to dict if needed
        if hasattr(data, '__dict__'):
            data_dict = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    data_dict[key] = value
            data = data_dict
        
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict or SQLAlchemy model, got {type(data)}")
        
        # Map pricing fields
        data['pricing'] = {
            'price': data.get('price', 0.0),
            'discounted_price': data.get('discounted_price', 0.0),
            'tax_rate': data.get('tax_rate', 0.0)
        }
        
        # Map inventory fields
        data['inventory'] = {
            'sku': data.get('sku', ''),
            'stock': data.get('stock', 0),
            'reorder_level': data.get('reorder_level'),
            'requires_prescription': data.get('requires_prescription', False),
            'is_active': data.get('is_active', True),
            'supports_online_payment': data.get('supports_online_payment') if data.get('supports_online_payment') is not None else True,
            'supports_cod': data.get('supports_cod') if data.get('supports_cod') is not None else True
        }
        
        # Map shipping fields if they exist
        if data.get('weight') or data.get('weight_unit') or data.get('dimensions'):
            shipping_data = {}
            if data.get('weight'):
                shipping_data['weight'] = data.get('weight')
            if data.get('weight_unit'):
                shipping_data['weight_unit'] = data.get('weight_unit')
            if data.get('dimensions'):
                shipping_data['dimensions'] = data.get('dimensions')
            data['shipping'] = shipping_data
        
        # Map warranty fields if they exist
        if data.get('warranty_period') or data.get('warranty_unit') or data.get('warranty_description'):
            warranty_data = {}
            if data.get('warranty_period'):
                warranty_data['period'] = data.get('warranty_period')
            if data.get('warranty_unit'):
                warranty_data['unit'] = data.get('warranty_unit')
            if data.get('warranty_description'):
                warranty_data['description'] = data.get('warranty_description')
            data['warranty'] = warranty_data
        
        # Map metadata fields if they exist
        if data.get('tags') or data.get('specifications'):
            metadata_data = {}
            if data.get('tags'):
                metadata_data['tags'] = data.get('tags')
            if data.get('specifications'):
                metadata_data['specifications'] = data.get('specifications')
            data['metadata'] = metadata_data
        
        return data
    
    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True