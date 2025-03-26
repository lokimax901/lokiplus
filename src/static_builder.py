import os
from flask import Flask
from flask.testing import FlaskClient
from app import app
import shutil
from pathlib import Path

def create_static_site():
    """Convert Flask templates to static HTML"""
    # Create a test client
    client = app.test_client()
    
    # Create build directory
    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Create static directory
    static_dir = build_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy static files
    src_static = Path("src/static")
    if src_static.exists():
        for item in src_static.glob("*"):
            if item.name == "config.js":
                continue
            dest = static_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
    
    # Generate static HTML
    with app.test_request_context():
        # Get index page
        response = client.get('/')
        if response.status_code == 200:
            index_html = response.data.decode('utf-8')
            # Fix asset paths
            index_html = index_html.replace('url_for(', '/static/')
            with open(build_dir / "index.html", "w", encoding='utf-8') as f:
                f.write(index_html)
        
        # Generate other pages if needed
        # Add more pages here as needed

if __name__ == "__main__":
    create_static_site() 