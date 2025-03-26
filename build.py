import os
import shutil
from pathlib import Path

def prepare_static_files():
    """Prepare static files for Netlify deployment."""
    # Create build directory if it doesn't exist
    build_dir = Path("src/static")
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy static assets (CSS, JS, images)
    static_src = Path("src/static")
    if static_src.exists():
        for item in static_src.glob("*"):
            if item.is_file():
                shutil.copy2(item, build_dir)
            elif item.is_dir():
                shutil.copytree(item, build_dir / item.name, dirs_exist_ok=True)

    # Copy templates as static HTML files
    templates_dir = Path("src/templates")
    if templates_dir.exists():
        # Copy index.html to the root of static directory
        index_template = templates_dir / "index.html"
        if index_template.exists():
            shutil.copy2(index_template, build_dir / "index.html")
        
        # Copy other templates to a templates directory
        templates_dest = build_dir / "templates"
        templates_dest.mkdir(exist_ok=True)
        for template in templates_dir.glob("*.html"):
            if template.name != "index.html":
                shutil.copy2(template, templates_dest)

    print("Static files prepared for Netlify deployment!")

if __name__ == "__main__":
    prepare_static_files() 