import os

# Project structure
structure = {
    "project": {
        "files": [
            "app.py",          
            "scraper.py",      
            "database.py",     
            "requirements.txt",
            ".env.example",
            "README.md"
        ],
        "folders": {
            "templates": [],
            "static": []
        }
    }
}

def create_structure(base_path, files, folders):
    os.makedirs(base_path, exist_ok=True)

    # Create files
    for file in files:
        open(os.path.join(base_path, file), 'w').close()

    # Create folders
    for folder, subfiles in folders.items():
        folder_path = os.path.join(base_path, folder)
        os.makedirs(folder_path, exist_ok=True)
        for subfile in subfiles:
            open(os.path.join(folder_path, subfile), 'w').close()

# Create the project structure
base_dir = "project"
create_structure(base_dir, structure["project"]["files"], structure["project"]["folders"])

print("Project structure created successfully!")
