import json
from datetime import datetime
from typing import Dict, Any

class UserTracker:
    def __init__(self, github_storage):
        self.github_storage = github_storage
        self.user_stats = self._load_user_stats()
    
    def _load_user_stats(self) -> Dict[str, Any]:
        """Load user statistics from GitHub"""
        if not self.github_storage:
            return {"unique_users": {}, "total_interactions": 0}
        
        try:
            # Load from a separate file for user stats
            original_path = self.github_storage.file_path
            self.github_storage.file_path = "user_stats.json"
            
            data = self.github_storage.load_data()
            self.github_storage.file_path = original_path
            return data
        except Exception as e:
            print(f"❌ Error loading user stats: {e}")
            # Restore original path in case of error
            if hasattr(self, 'github_storage') and self.github_storage:
                self.github_storage.file_path = "study_materials.json"
            return {"unique_users": {}, "total_interactions": 0}
    
    def _save_user_stats(self) -> bool:
        """Save user statistics to GitHub"""
        if not self.github_storage:
            return False
        
        try:
            original_path = self.github_storage.file_path
            self.github_storage.file_path = "user_stats.json"
            
            success = self.github_storage.save_data(self.user_stats)
            self.github_storage.file_path = original_path
            return success
        except Exception as e:
            print(f"❌ Error saving user stats: {e}")
            if hasattr(self, 'github_storage') and self.github_storage:
                self.github_storage.file_path = "study_materials.json"
            return False
    
    def track_user(self, user_id: int, username: str, first_name: str, action: str = "interaction"):
        """Track user interaction"""
        try:
            user_id_str = str(user_id)
            
            if user_id_str not in self.user_stats["unique_users"]:
                self.user_stats["unique_users"][user_id_str] = {
                    "username": username or "No username",
                    "first_name": first_name or "Unknown",
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
            
            # Save to GitHub in background (don't block on failure)
            self._save_user_stats()
            
        except Exception as e:
            print(f"❌ Error tracking user: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            unique_users_count = len(self.user_stats.get("unique_users", {}))
            total_interactions = self.user_stats.get("total_interactions", 0)
            
            # Calculate active users (last 30 days)
            active_users = 0
            thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            
            for user_data in self.user_stats.get("unique_users", {}).values():
                try:
                    last_seen = datetime.fromisoformat(user_data["last_seen"]).timestamp()
                    if last_seen > thirty_days_ago:
                        active_users += 1
                except:
                    continue
            
            return {
                "unique_users": unique_users_count,
                "active_users": active_users,
                "total_interactions": total_interactions,
                "user_details": self.user_stats.get("unique_users", {})
            }
        except Exception as e:
            print(f"❌ Error getting user stats: {e}")
            return {"unique_users": 0, "active_users": 0, "total_interactions": 0}

# Global instance
user_tracker = None

def init_user_tracker(github_storage):
    """Initialize user tracker"""
    global user_tracker
    try:
        user_tracker = UserTracker(github_storage)
        print("✅ User tracker initialized")
        return user_tracker
    except Exception as e:
        print(f"❌ Failed to initialize user tracker: {e}")
        return None

def track_user_interaction(user_id: int, username: str, first_name: str, action: str = "interaction"):
    """Track user interaction"""
    global user_tracker
    if user_tracker:
        user_tracker.track_user(user_id, username, first_name, action)
    else:
        print(f"⚠️ User tracker not available for user {user_id}")

def get_user_stats():
    """Get user statistics"""
    global user_tracker
    if user_tracker:
        return user_tracker.get_stats()
    return {"unique_users": 0, "active_users": 0, "total_interactions": 0}
