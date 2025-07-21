import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
import aiofiles
from pathlib import Path

class FileService:
    """Service for handling file uploads"""
    
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        
        # Create upload directories if they don't exist
        self.upload_dir.mkdir(exist_ok=True)
        (self.upload_dir / "categories").mkdir(exist_ok=True)
        (self.upload_dir / "products").mkdir(exist_ok=True)
    
    def _validate_image_file(self, file: UploadFile) -> None:
        """Validate uploaded image file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(self.allowed_extensions)}"
            )
        
        # Check content type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
    
    async def save_image(self, file: UploadFile, folder: str) -> str:
        """
        Save uploaded image file and return the file path
        
        Args:
            file: The uploaded file
            folder: The subfolder (e.g., 'categories', 'products')
            
        Returns:
            str: The relative file path
        """
        # Validate file
        self._validate_image_file(file)
        
        # Check file size
        content = await file.read()
        if len(content) > self.max_file_size:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Create file path
        folder_path = self.upload_dir / folder
        file_path = folder_path / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Return relative path
        return f"uploads/{folder}/{unique_filename}"
    
    async def delete_image(self, file_path: str) -> bool:
        """
        Delete an image file
        
        Args:
            file_path: The relative file path
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            full_path = Path(file_path)
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_absolute_path(self, file_path: str) -> str:
        """Get absolute path for a relative file path"""
        return str(Path(file_path).absolute())
