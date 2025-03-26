import os
import shutil
from pathlib import Path

def safe_copy(src, dst):
    """Safely copy a file, removing the destination first if it exists."""
    try:
        if dst.exists():
            if dst.is_file():
                dst.unlink()
            elif dst.is_dir():
                shutil.rmtree(dst)
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        return True
    except Exception as e:
        print(f"Error copying {src} to {dst}: {e}")
        return False

def prepare_static_files():
    """Prepare static files for Netlify deployment."""
    try:
        # Create build directory if it doesn't exist
        build_dir = Path("build")
        build_dir.mkdir(parents=True, exist_ok=True)

        # Create static directory in build
        static_build_dir = build_dir / "static"
        static_build_dir.mkdir(parents=True, exist_ok=True)

        # Copy static assets (CSS, JS, images)
        static_src = Path("src/static")
        if static_src.exists():
            for item in static_src.glob("*"):
                # Skip config.js as it's environment-specific
                if item.name == "config.js":
                    continue
                    
                dest_path = static_build_dir / item.name
                safe_copy(item, dest_path)

        # Copy templates as static HTML files
        templates_dir = Path("src/templates")
        if templates_dir.exists():
            # Copy index.html to the root of build directory
            index_template = templates_dir / "index.html"
            if index_template.exists():
                safe_copy(index_template, build_dir / "index.html")
            
            # Copy other templates to a templates directory
            templates_dest = build_dir / "templates"
            templates_dest.mkdir(exist_ok=True)
            for template in templates_dir.glob("*.html"):
                if template.name != "index.html":
                    safe_copy(template, templates_dest / template.name)

        print("Static files prepared for Netlify deployment!")
        return True

    except Exception as e:
        print(f"Error preparing static files: {e}")
        return False

if __name__ == "__main__":
    prepare_static_files() 