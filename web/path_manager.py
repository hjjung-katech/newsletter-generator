"""
Path Manager for Newsletter Generator Web Application
Handles path resolution for both development and PyInstaller exe environments
"""

import os
import sys
from pathlib import Path


class PathManager:
    """Centralized path management for development and exe environments"""
    
    def __init__(self):
        self._is_frozen = getattr(sys, 'frozen', False)
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup all necessary paths based on environment"""
        if self._is_frozen:
            # PyInstaller exe environment - use dist/ as base
            self.exe_dir = Path(sys.executable).parent
            self.base_dir = self.exe_dir
            print(f"[PATH] PyInstaller mode - exe_dir: {self.exe_dir}")
        else:
            # Development environment - use web/ as base
            self.base_dir = Path(__file__).parent
            print(f"[PATH] Development mode - base_dir: {self.base_dir}")
        
        # Core data paths
        self.database_path = self.base_dir / "storage.db"
        self.output_dir = self.base_dir / "output"
        self.logs_dir = self.base_dir / "logs"
        self.config_dir = self.base_dir / "config"
        self.templates_dir = self.base_dir / "templates"
        
        # Ensure directories exist
        self._ensure_directories()
        
        print(f"[PATH] Database: {self.database_path}")
        print(f"[PATH] Output: {self.output_dir}")
        print(f"[PATH] Logs: {self.logs_dir}")
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        dirs_to_create = [
            self.output_dir,
            self.logs_dir,
            self.config_dir,
            self.output_dir / "intermediate_processing"
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"[PATH] Ensured directory: {dir_path}")
    
    @property
    def is_frozen(self):
        """Check if running in PyInstaller exe environment"""
        return self._is_frozen
    
    def get_database_path(self):
        """Get database file path as string"""
        return str(self.database_path)
    
    def get_output_dir(self):
        """Get output directory path as string"""
        return str(self.output_dir)
    
    def get_logs_dir(self):
        """Get logs directory path as string"""
        return str(self.logs_dir)
    
    def get_config_dir(self):
        """Get config directory path as string"""
        return str(self.config_dir)
    
    def get_templates_dir(self):
        """Get templates directory path as string"""
        return str(self.templates_dir)
    
    def get_newsletter_file_path(self, filename):
        """Get full path for a newsletter file"""
        return str(self.output_dir / filename)
    
    def list_newsletter_files(self, pattern="*.html"):
        """List newsletter files in output directory"""
        try:
            files = list(self.output_dir.glob(pattern))
            return [f.name for f in files if f.is_file()]
        except Exception as e:
            print(f"[PATH] Error listing files: {e}")
            return []
    
    def file_exists(self, filename):
        """Check if newsletter file exists"""
        file_path = self.output_dir / filename
        return file_path.exists()


# Global instance
_path_manager = None

def get_path_manager():
    """Get global PathManager instance"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager