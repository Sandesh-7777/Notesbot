import json
import base64
import requests
import os
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
    
    def load_data(self) -> Dict[str, Any]:
        """Load JSON data from GitHub with better error handling"""
        try:
            print(f"🔄 Loading data from GitHub: {self.repo}/{self.file_path}")
            url = f"{self.base_url}/{self.file_path}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                content = response.json()['content']
                # GitHub API returns base64 with newlines, so we need to clean it
                cleaned_content = content.replace('\n', '')
                decoded_content = base64.b64decode(cleaned_content).decode('utf-8')
                data = json.loads(decoded_content)
                print(f"✅ Successfully loaded {len(data)} branches from GitHub")
                return data
            elif response.status_code == 404:
                print("⚠️ File not found on GitHub, creating initial structure...")
                initial_data = self._get_initial_data()
                self.save_data(initial_data)
                return initial_data
            else:
                print(f"❌ GitHub API Error {response.status_code}: {response.text}")
                return self._get_initial_data()
                
        except Exception as e:
            print(f"❌ Error loading data from GitHub: {e}")
            return self._get_initial_data()
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save JSON data to GitHub with better error handling"""
        try:
            print(f"💾 Attempting to save data to GitHub...")
            print(f"📊 Data to save: {len(data)} branches, {self._count_materials(data)} materials")
            
            # First, get the current file to get its SHA (if exists)
            url = f"{self.base_url}/{self.file_path}"
            get_response = requests.get(url, headers=self.headers, timeout=10)
            
            sha = None
            if get_response.status_code == 200:
                sha = get_response.json().get('sha')
                print(f"📝 Found existing file, SHA: {sha[:10]}...")
            elif get_response.status_code == 404:
                print("📄 Creating new file on GitHub...")
            else:
                print(f"❌ Error checking existing file: {get_response.status_code}")
                return False
            
            # Prepare the content
            content = json.dumps(data, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content.encode('utf-8')).decode()
            
            # Prepare the payload
            payload = {
                "message": f"Bot update: Study materials - {len(data)} branches, {self._count_materials(data)} materials",
                "content": encoded_content,
                "branch": "main"
            }
            
            if sha:
                payload["sha"] = sha
            
            print(f"🚀 Sending request to GitHub API...")
            # Update the file
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                print("✅ Data successfully saved to GitHub")
                print(f"📎 Commit SHA: {response.json().get('commit', {}).get('sha', 'N/A')}")
                return True
            else:
                print(f"❌ Error saving to GitHub: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving data to GitHub: {e}")
            return False
    
    def _count_materials(self, data: Dict[str, Any]) -> int:
        """Count total number of materials"""
        count = 0
        for branch, semesters in data.items():
            for semester, subjects in semesters.items():
                for subject, subject_data in subjects.items():
                    count += len(subject_data.get("materials", []))
        return count
    
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
        print("⚠️ GitHub storage not configured. Using local file as fallback.")
        print("ℹ️ Please set GITHUB_TOKEN and GITHUB_REPO environment variables")
        return None
    
    github_storage = GitHubStorage(token, repo)
    print(f"✅ GitHub storage initialized for repo: {repo}")
    return github_storage

def load_materials():
    """Load study materials from GitHub or local file"""
    global github_storage
    
    # Try GitHub first if configured
    if github_storage:
        try:
            data = github_storage.load_data()
            if data:
                return data
        except Exception as e:
            print(f"❌ GitHub load failed: {e}")
    
    # Fallback to local file
    try:
        if os.path.exists('study_materials.json'):
            with open('study_materials.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print("✅ Data loaded from local file")
                return data
        else:
            print("📁 Creating new local data file")
            initial_data = {
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
            save_materials(initial_data)
            return initial_data
    except Exception as e:
        print(f"❌ Error loading local materials: {e}")
        return {}

def save_materials(materials):
    """Save study materials to GitHub or local file"""
    global github_storage
    
    print(f"💾 save_materials called with {len(materials)} branches")
    
    # Try GitHub first if configured
    if github_storage:
        print("🔄 Attempting to save to GitHub...")
        success = github_storage.save_data(materials)
        if success:
            print("💫 Data saved to GitHub successfully")
            # Also update local file as backup
            _save_local_backup(materials)
            return
        else:
            print("❌ GitHub save failed, falling back to local")
    
    # Fallback to local file
    _save_local_backup(materials)

def _save_local_backup(materials):
    """Save backup to local file"""
    try:
        with open('study_materials.json', 'w', encoding='utf-8') as f:
            json.dump(materials, f, indent=2, ensure_ascii=False)
        print("💾 Data saved to local file as backup")
        
        # Debug: Print what was saved
        total_materials = 0
        for branch, semesters in materials.items():
            for semester, subjects in semesters.items():
                for subject, subject_data in subjects.items():
                    total_materials += len(subject_data.get("materials", []))
        print(f"📊 Local backup contains {total_materials} materials across {len(materials)} branches")
        
    except Exception as e:
        print(f"❌ Error saving local backup: {e}")
