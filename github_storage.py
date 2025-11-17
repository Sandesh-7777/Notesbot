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
            "Accept": "application/vnd.github.v3+json"
        }
    
    def load_data(self) -> Dict[str, Any]:
        """Load JSON data from GitHub"""
        try:
            url = f"{self.base_url}/{self.file_path}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                content = response.json()['content']
                decoded_content = base64.b64decode(content).decode('utf-8')
                print("✅ Data loaded from GitHub successfully")
                return json.loads(decoded_content)
            elif response.status_code == 404:
                print("⚠️ File not found on GitHub, creating initial structure...")
                initial_data = self._get_initial_data()
                self.save_data(initial_data)
                return initial_data
            else:
                print(f"❌ Error loading from GitHub: {response.status_code} - {response.text}")
                return self._get_initial_data()
                
        except Exception as e:
            print(f"❌ Error loading data from GitHub: {e}")
            return self._get_initial_data()
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        """Save JSON data to GitHub"""
        try:
            # First, get the current file to get its SHA (if exists)
            url = f"{self.base_url}/{self.file_path}"
            get_response = requests.get(url, headers=self.headers)
            
            sha = None
            if get_response.status_code == 200:
                sha = get_response.json().get('sha')
            
            # Prepare the content
            content = json.dumps(data, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content.encode('utf-8')).decode()
            
            # Prepare the payload
            payload = {
                "message": f"Bot update: Study materials - {len(data)} branches",
                "content": encoded_content,
                "branch": "main"
            }
            
            if sha:
                payload["sha"] = sha
            
            # Update the file
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 201]:
                print("✅ Data successfully saved to GitHub")
                return True
            else:
                print(f"❌ Error saving to GitHub: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving data to GitHub: {e}")
            return False
    
    def _get_initial_data(self) -> Dict[str, Any]:
        """Get initial data structure"""
        return {
            "CSE": {
                "4": {
                    "DBMS": {
                        "materials": [
                            {
                                "title": "DBMS Module 2 Notes", 
                                "file_id": "", 
                                "type": "pdf", 
                                "keywords": ["dbms", "database", "module2"]
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
            return github_storage.load_data()
        except Exception as e:
            print(f"❌ GitHub load failed, using local fallback: {e}")
    
    # Fallback to local file
    try:
        if os.path.exists('study_materials.json'):
            with open('study_materials.json', 'r', encoding='utf-8') as f:
                print("✅ Data loaded from local file")
                return json.load(f)
        else:
            initial_data = {
                "CSE": {
                    "4": {
                        "DBMS": {
                            "materials": [
                                {"title": "DBMS Module 2 Notes", "file_id": "", "type": "pdf", "keywords": ["dbms", "database", "module2"]},
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
    
    # Try GitHub first if configured
    if github_storage:
        success = github_storage.save_data(materials)
        if success:
            return
    
    # Fallback to local file
    try:
        with open('study_materials.json', 'w', encoding='utf-8') as f:
            json.dump(materials, f, indent=2, ensure_ascii=False)
        print("✅ Data saved to local file")
    except Exception as e:
        print(f"❌ Error saving local materials: {e}")
