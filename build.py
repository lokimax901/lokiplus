import os
import shutil
from pathlib import Path
from static_builder import create_static_site

def build():
    """Build the static site for Netlify deployment"""
    try:
        # Clean up existing build directory
        build_dir = Path("build")
        if build_dir.exists():
            shutil.rmtree(build_dir)
        
        # Create static site
        create_static_site()
        
        print("Static site built successfully!")
        return True
    except Exception as e:
        print(f"Error building static site: {e}")
        return False

if __name__ == "__main__":
    build() 