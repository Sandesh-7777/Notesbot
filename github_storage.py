import json
import base64
import requests
import os
import time
from typing import Dict, Any

class GitHubStorage:
    def __init__(self, token: str, repo: str, file_path: str = "study_materials.json"):
        self.token = token
        self.repo = repo
        self.file_path = file_path
        self.base_url = f"https://api.github.com/repos/{repo}/contents"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        self.last_sync_time = 0
        self.sync_interval = 60  # Sync at most once per minute
    
    def load_data(self) -> Dict[str, Any]:
        """Load JSON data from GitHub with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔄 Loading data from GitHub (attempt {attempt + 1})...")
                url = f"{self.base_url}/{self.file_path}"
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    content = response.json()['content']
                    cleaned_content = content.replace('\n', '')
                    decoded_content = base64.b64decode(cleaned_content).decode('utf-8')
                    data = json.loads(decoded_content)
                    print(f"✅ Successfully loaded {len(data)} branches from GitHub")
                    return data
                elif response.status_code == 404:
                    print("⚠️ File not found on GitHub, using local file...")
                    return self._load_local_data()
                else:
                    print(f"❌ GitHub API Error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return self._load_local_data()
                    
            except Exception as e:
                print(f"❌ Error loading from GitHub (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return self._load_local_data()
        
        return self._load_local_data()
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save JSON data to GitHub with retry logic"""
        # Always save locally first
        self._save_local_data(data)
        
        # Rate limiting: don't sync to GitHub too frequently
        current_time = time.time()
        if current_time - self.last_sync_time < self.sync_interval:
            print("⏳ GitHub sync skipped (rate limiting)")
            return True
            
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"💾 Attempting GitHub sync (attempt {attempt + 1})...")
                
                # Get current file SHA
                url = f"{self.base_url}/{self.file_path}"
                get_response = requests.get(url, headers=self.headers, timeout=10)
                
                sha = None
                if get_response.status_code == 200:
                    sha = get_response.json().get('sha')
                    print(f"📝 Found existing file on GitHub")
                elif get_response.status_code != 404:
                    print(f"❌ Error checking GitHub file: {get_response.status_code}")
                    continue
                
                # Prepare content
                content = json.dumps(data, indent=2, ensure_ascii=False)
                encoded_content = base64.b64encode(content.encode('utf-8')).decode()
                
                # Prepare payload
                payload = {
                    "message": f"Bot auto-sync: {len(data)} branches, {self._count_materials(data)} materials",
                    "content": encoded_content,
                    "branch": "main"
                }
                
                if sha:
                    payload["sha"] = sha
                
                # Send to GitHub
                response = requests.put(url, headers=self.headers, json=payload, timeout=30)
                
                if response.status_code in [200, 201]:
                    self.last_sync_time = current_time
                    print("✅ Data successfully synced to GitHub")
                    return True
                else:
                    print(f"❌ GitHub sync failed: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    return False
                    
            except Exception as e:
                print(f"❌ GitHub sync error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
        
        print("⚠️ GitHub sync failed after retries, but local save was successful")
        return False
    
    def _count_materials(self, data: Dict[str, Any]) -> int:
        """Count total number of materials"""
        count = 0
        for branch, semesters in data.items():
            for semester, subjects in semesters.items():
                for subject, subject_data in subjects.items():
                    count += len(subject_data.get("materials", []))
        return count
    
    def _load_local_data(self) -> Dict[str, Any]:
        """Load data from local file"""
        try:
            if os.path.exists('study_materials.json'):
                with open('study_materials.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ Loaded {len(data)} branches from local file")
                    return data
            else:
                print("📁 No local file found, creating initial structure")
                return self._get_initial_data()
        except Exception as e:
            print(f"❌ Error loading local file: {e}")
            return self._get_initial_data()
    
    def _save_local_data(self, data: Dict[str, Any]) -> bool:
        """Save data to local file"""
        try:
            with open('study_materials.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Debug info
            total_materials = self._count_materials(data)
            print(f"💾 Local save: {len(data)} branches, {total_materials} materials")
            return True
        except Exception as e:
            print(f"❌ Error saving local file: {e}")
            return False
    
    def _get_initial_data(self) -> Dict[str, Any]:
        """Get initial data structure"""
        return {
            "CSE": {
                "4": {
                    "DBMS": {
                        "materials": [
                            {
                                "title": "DBMS Module 1 Notes",
                                "file_id": "BQACAgUAAxkBAAMHaO6L7HpmEKJr6ZKMvC6NQ5uaPLAAAvUVAAJM_nlX1dCf5s3L2Fc2BA",
                                "type": "document", 
                                "keywords": ["dbms", "database", "module1"]
                            },
                        ]
                    }
                }
            }
        }

# Global instance
github_storage = None

def init_github_storage():
    """Initialize GitHub storage with environment variables"""
    global github_storage
    token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')
    
    if not token or not repo:
        print("⚠️ GitHub storage not configured. Using local-only mode.")
        print("ℹ️ Set GITHUB_TOKEN and GITHUB_REPO for cloud sync")
        return None
    
    # Test the token and repo
    test_url = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"token {token}"}
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            github_storage = GitHubStorage(token, repo)
            print(f"✅ GitHub storage initialized for: {repo}")
            return github_storage
        else:
            print(f"❌ GitHub token/repo validation failed: {response.status_code}")
            print("⚠️ Falling back to local-only mode")
            return None
    except Exception as e:
        print(f"❌ GitHub connection test failed: {e}")
        print("⚠️ Falling back to local-only mode")
        return None

def load_materials():
    """Load study materials - always works with local fallback"""
    global github_storage
    
    if github_storage:
        try:
            return github_storage.load_data()
        except Exception as e:
            print(f"❌ GitHub load failed, using local: {e}")
    
    # Fallback to local
    if github_storage:
        return github_storage._load_local_data()
    else:
        # Create basic GitHub storage instance for local operations
        temp_storage = GitHubStorage("dummy", "dummy/repo")
        return temp_storage._load_local_data()

def save_materials(materials):
    """Save study materials - always works with local fallback"""
    global github_storage
    
    print(f"🚀 SAVE_MATERIALS CALLED - {len(materials)} branches")
    
    if github_storage:
        try:
            success = github_storage.save_data(materials)
            if success:
                print("🎉 Save completed with GitHub sync")
            else:
                print("💾 Save completed (local only, GitHub sync failed)")
        except Exception as e:
            print(f"❌ GitHub save error, saved locally: {e}")
            if github_storage:
                github_storage._save_local_data(materials)
    else:
        # Local-only mode
        temp_storage = GitHubStorage("dummy", "dummy/repo")
        temp_storage._save_local_data(materials)
        print("💾 Save completed (local only)")
