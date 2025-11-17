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
    
    def load_data(self) -> Dict[str, Any]:
        """Load JSON data from GitHub only - no local fallback"""
        try:
            print(f"📥 Loading {self.file_path} from GitHub...")
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
                print("⚠️ File not found on GitHub, creating initial structure...")
                initial_data = self._get_initial_data()
                self.save_data(initial_data)
                return initial_data
            else:
                print(f"❌ GitHub API Error {response.status_code}: {response.text}")
                # Return empty data instead of local fallback
                return self._get_initial_data()
                
        except Exception as e:
            print(f"❌ Error loading from GitHub: {e}")
            # Return empty data instead of local fallback
            return self._get_initial_data()
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save JSON data to GitHub only - no local saving"""
        try:
            print(f"💾 Saving {len(data)} branches to GitHub...")
            
            # Get current file SHA
            url = f"{self.base_url}/{self.file_path}"
            get_response = requests.get(url, headers=self.headers, timeout=10)
            
            sha = None
            if get_response.status_code == 200:
                sha = get_response.json().get('sha')
                print("📝 Updating existing GitHub file...")
            elif get_response.status_code == 404:
                print("📄 Creating new file on GitHub...")
            else:
                print(f"❌ Cannot access GitHub file: {get_response.status_code}")
                return False
            
            # Prepare content
            content = json.dumps(data, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content.encode('utf-8')).decode()
            
            # Prepare payload
            payload = {
                "message": f"Bot update: {len(data)} branches, {self._count_materials(data)} materials",
                "content": encoded_content,
                "branch": "main"
            }
            
            if sha:
                payload["sha"] = sha
            
            # Send to GitHub
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                print("✅ Data successfully saved to GitHub!")
                return True
            else:
                print(f"❌ GitHub save failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ GitHub save error: {e}")
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
                                "title": "Sample Material",
                                "file_id": "",
                                "type": "document", 
                                "keywords": ["sample"]
                            },
                        ]
                    }
                }
            }
        }

# Global instance
github_storage = None

def init_github_storage():
    """Initialize GitHub storage"""
    global github_storage
    
    token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')
    
    if not token or not repo:
        print("❌ GitHub storage: DISABLED - missing token or repo")
        return None
    
    # Test connection
    test_url = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"token {token}"}
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            github_storage = GitHubStorage(token, repo)
            print(f"✅ GitHub storage initialized: {repo}")
            return github_storage
        else:
            print(f"❌ GitHub connection failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ GitHub connection failed: {e}")
        return None

def load_materials():
    """Load study materials from GitHub only"""
    global github_storage
    
    if not github_storage:
        print("❌ GitHub storage not available")
        return {}
    
    return github_storage.load_data()

def save_materials(materials):
    """Save study materials to GitHub only"""
    global github_storage
    
    if not github_storage:
        print("❌ GitHub storage not available - cannot save")
        return
    
    github_storage.save_data(materials)
