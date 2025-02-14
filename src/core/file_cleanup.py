# src/core/file_cleanup.py
import time
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import schedule
import threading

class AudioFileCleanup:
    def __init__(self, 
                 directory: str,
                 max_age_hours: int = 24,
                 min_free_space_mb: int = 1000,
                 cleanup_interval_minutes: int = 30):
        """
        Initialize the audio file cleanup service.
        
        Args:
            directory: Directory containing audio files to clean
            max_age_hours: Maximum age of files before deletion (default 24 hours)
            min_free_space_mb: Minimum free space to maintain in MB (default 1GB)
            cleanup_interval_minutes: How often to run cleanup (default 30 minutes)
        """
        self.directory = Path(directory)
        self.max_age_hours = max_age_hours
        self.min_free_space_bytes = min_free_space_mb * 1024 * 1024
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.cleanup_thread: Optional[threading.Thread] = None
        self.last_cleanup: Optional[datetime] = None
        self.cleanup_stats: Dict = {
            "last_run": None,
            "files_deleted": 0,
            "space_freed": 0,
            "errors": 0
        }

    def get_file_age_hours(self, filepath: Path) -> float:
        """Calculate file age in hours"""
        try:
            mtime = filepath.stat().st_mtime
            age = time.time() - mtime
            return age / 3600
        except Exception as e:
            self.logger.error(f"Error getting age for {filepath}: {e}")
            return float('inf')

    def get_free_space(self) -> int:
        """Get free space in bytes for the directory's filesystem"""
        try:
            if not self.directory.exists():
                return 0
            total, used, free = shutil.disk_usage(str(self.directory))
            return free
        except Exception as e:
            self.logger.error(f"Error getting free space: {e}")
            return 0

    def should_delete_file(self, filepath: Path) -> bool:
        """Determine if a file should be deleted based on age and pattern"""
        try:
            # Only process .wav files
            if filepath.suffix != '.wav':
                return False
                
            # Check if file starts with realtime_ prefix
            if not filepath.stem.startswith('realtime_'):
                return False
                
            # Check file age
            age_hours = self.get_file_age_hours(filepath)
            return age_hours >= self.max_age_hours
            
        except Exception as e:
            self.logger.error(f"Error checking file {filepath}: {e}")
            return False

    def cleanup_files(self) -> None:
        """Perform the file cleanup operation"""
        try:
            if not self.directory.exists():
                self.logger.warning(f"Directory {self.directory} does not exist")
                return

            files_deleted = 0
            space_freed = 0
            errors = 0

            # First pass: Delete old files
            for filepath in self.directory.iterdir():
                try:
                    if self.should_delete_file(filepath):
                        size = filepath.stat().st_size
                        filepath.unlink()
                        files_deleted += 1
                        space_freed += size
                        self.logger.info(f"Deleted old file: {filepath}")
                except Exception as e:
                    self.logger.error(f"Error deleting file {filepath}: {e}")
                    errors += 1

            # Second pass: If we're still low on space, delete more files
            free_space = self.get_free_space()
            if free_space < self.min_free_space_bytes:
                self.logger.warning(
                    f"Low on space ({free_space / (1024*1024):.2f}MB free), "
                    f"minimum required: {self.min_free_space_bytes / (1024*1024):.2f}MB"
                )
                files = sorted(
                    [f for f in self.directory.iterdir() if f.suffix == '.wav'],
                    key=lambda x: x.stat().st_mtime
                )
                
                for filepath in files:
                    try:
                        if self.get_free_space() >= self.min_free_space_bytes:
                            break
                            
                        size = filepath.stat().st_size
                        filepath.unlink()
                        files_deleted += 1
                        space_freed += size
                        self.logger.info(f"Deleted file due to space constraints: {filepath}")
                    except Exception as e:
                        self.logger.error(f"Error deleting file {filepath}: {e}")
                        errors += 1

            # Update stats
            self.cleanup_stats.update({
                "last_run": datetime.now(),
                "files_deleted": files_deleted,
                "space_freed": space_freed,
                "errors": errors
            })

            self.logger.info(
                f"Cleanup completed: {files_deleted} files deleted, "
                f"{space_freed / (1024*1024):.2f}MB freed, {errors} errors. "
                f"Free space: {self.get_free_space() / (1024*1024):.2f}MB"
            )

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            self.cleanup_stats["errors"] += 1

    def _cleanup_job(self) -> None:
        """Wrapper for cleanup_files to be used with scheduler"""
        self.cleanup_files()
        self.last_cleanup = datetime.now()

    def start(self) -> None:
        """Start the cleanup service in a background thread"""
        if self.is_running:
            self.logger.warning("Cleanup service is already running")
            return

        def run_scheduler():
            self.is_running = True
            schedule.every(self.cleanup_interval_minutes).minutes.do(self._cleanup_job)
            
            # Run initial cleanup
            self._cleanup_job()
            
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        self.cleanup_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.cleanup_thread.start()
        self.logger.info(
            f"Started cleanup service (interval: {self.cleanup_interval_minutes}m, "
            f"max age: {self.max_age_hours}h, min free space: {self.min_free_space_bytes/(1024*1024)}MB)"
        )

    def stop(self) -> None:
        """Stop the cleanup service"""
        self.is_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=60)
            self.cleanup_thread = None
        self.logger.info("Stopped cleanup service")

    def get_status(self) -> Dict:
        """Get current status of the cleanup service"""
        return {
            "is_running": self.is_running,
            "last_cleanup": self.last_cleanup,
            "directory": str(self.directory),
            "free_space_mb": self.get_free_space() / (1024*1024),
            "stats": self.cleanup_stats
        }
