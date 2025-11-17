import os
from github_storage import init_github_storage, load_materials, save_materials

# Test the GitHub integration
if __name__ == "__main__":
    init_github_storage()
    
    # Load current data
    data = load_materials()
    print(f"Loaded {len(data)} branches from storage")
    
    # Test save
    success = save_materials(data)
    print(f"Save successful: {success}")
