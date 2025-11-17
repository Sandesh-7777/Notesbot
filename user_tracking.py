import json
import os
from datetime import datetime
from typing import Dict, Any

class UserTracker:
    def __init__(self, github_storage, stats_file: str = "user_stats.json"):
        self.github_storage = github_storage
        self.stats_file = stats_file
        self.user_stats = self._load_user_stats()
    
    def _load_user_stats(self) -> Dict[str, Any]:
        """Load user statistics from GitHub"""
        if not self.github_storage:
            return {"unique_users": {}, "total_interactions": 0}
        
        # Temporarily change the file path for user stats
        original_path = self.github_storage.file_path
        self.github_storage.file_path = self.stats_file
        
        try:
            data = self.github_storage.load_data()
            # Restore original path
            self.github_storage.file_path = original_path
            return data
        except:
            # Restore original path
            self.github_storage.file_path = original_path
            return {"unique_users": {}, "total_interactions": 0}
    
    def _save_user_stats(self) -> bool:
        """Save user statistics to GitHub"""
        if not self.github_storage:
            return False
        
        # Temporarily change the file path for user stats
        original_path = self.github_storage.file_path
        self.github_storage.file_path = self.stats_file
        
        try:
            success = self.github_storage.save_data(self.user_stats)
            # Restore original path
            self.github_storage.file_path = original_path
            return success
        except:
            # Restore original path
            self.github_storage.file_path = original_path
            return False
    
    def track_user(self, user_id: int, username: str, first_name: str, action: str = "interaction"):
        """Track user interaction"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_stats["unique_users"]:
            self.user_stats["unique_users"][user_id_str] = {
                "username": username,
                "first_name": first_name,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "total_interactions": 1,
                "actions": {action: 1}
            }
        else:
            self.user_stats["unique_users"][user_id_str]["last_seen"] = datetime.now().isoformat()
            self.user_stats["unique_users"][user_id_str]["total_interactions"] += 1
            self.user_stats["unique_users"][user_id_str]["actions"][action] = \
                self.user_stats["unique_users"][user_id_str]["actions"].get(action, 0) + 1
        
        self.user_stats["total_interactions"] = self.user_stats.get("total_interactions", 0) + 1
        
        # Save to GitHub (but don't block on failure)
        try:
            self._save_user_stats()
        except:
            pass  # Fail silently for user tracking
    
    def get_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        unique_users_count = len(self.user_stats.get("unique_users", {}))
        total_interactions = self.user_stats.get("total_interactions", 0)
        
        # Calculate active users (last 30 days)
        active_users = 0
        thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        
        for user_data in self.user_stats.get("unique_users", {}).values():
            last_seen = datetime.fromisoformat(user_data["last_seen"]).timestamp()
            if last_seen > thirty_days_ago:
                active_users += 1
        
        return {
            "unique_users": unique_users_count,
            "active_users": active_users,
            "total_interactions": total_interactions,
            "user_details": self.user_stats.get("unique_users", {})
        }

# Global instance
user_tracker = None

def init_user_tracker(github_storage):
    """Initialize user tracker"""
    global user_tracker
    user_tracker = UserTracker(github_storage)
    return user_tracker

def track_user_interaction(user_id: int, username: str, first_name: str, action: str = "interaction"):
    """Track user interaction"""
    global user_tracker
    if user_tracker:
        user_tracker.track_user(user_id, username, first_name, action)

def get_user_stats():
    """Get user statistics"""
    global user_tracker
    if user_tracker:
        return user_tracker.get_stats()
    return {"unique_users": 0, "active_users": 0, "total_interactions": 0}
