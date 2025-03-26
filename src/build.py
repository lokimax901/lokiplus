import os
import shutil
from pathlib import Path

def safe_copy(src, dst):
    """Safely copy a file, creating parent directories if needed."""
    try:
        # Create parent directories if they don't exist
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Only copy if source and destination are different
        if src != dst and src.exists():
            shutil.copy2(src, dst)
            print(f"Copied {src.name} to {dst.parent}")
    except Exception as e:
        print(f"Error copying {src.name}: {str(e)}")

def clean_directory(directory):
    """Clean a directory without deleting the directory itself."""
    if directory.exists():
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f"Cleaned directory: {directory}")

def build_static_files():
    """Build and organize static files for production."""
    # Setup directories
    build_dir = Path('build')
    static_dir = Path('static')
    template_dir = Path('templates')
    
    # Clean and recreate build directory
    if build_dir.exists():
        clean_directory(build_dir)
    else:
        build_dir.mkdir(exist_ok=True)
    print("Prepared build directory")
    
    # Copy template files to build directory
    if template_dir.exists():
        for template in template_dir.glob('*.html'):
            safe_copy(template, build_dir / template.name)
    
    # Copy static assets if they exist
    if static_dir.exists():
        # Copy CSS files
        for css in static_dir.glob('css/*.css'):
            safe_copy(css, build_dir / 'css' / css.name)
        
        # Copy JavaScript files
        for js in static_dir.glob('js/*.js'):
            safe_copy(js, build_dir / 'js' / js.name)
        
        # Copy images
        for img in static_dir.glob('img/*'):
            safe_copy(img, build_dir / 'img' / img.name)
    
    # Create a simple 404 page
    not_found_page = build_dir / '404.html'
    with open(not_found_page, 'w') as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Page Not Found - LokiPlus</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 40em; margin: 0 auto; padding: 2em; }
        h1 { color: #2563eb; }
        .back-link { display: inline-block; margin-top: 1em; color: #2563eb; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The page you're looking for doesn't exist or has been moved.</p>
    <a href="/" class="back-link">← Go back home</a>
</body>
</html>
        """.strip())
    print("Created 404.html")
    
    # Clean and prepare static directory for final output
    if static_dir.exists():
        clean_directory(static_dir)
    else:
        static_dir.mkdir(exist_ok=True)
    
    # Move everything from build to static
    for item in build_dir.iterdir():
        if item.is_file():
            safe_copy(item, static_dir / item.name)
        elif item.is_dir():
            for file in item.rglob('*'):
                if file.is_file():
                    relative_path = file.relative_to(build_dir)
                    safe_copy(file, static_dir / relative_path)
    
    # Clean up build directory
    shutil.rmtree(build_dir)
    print("Build completed successfully!")

if __name__ == '__main__':
    build_static_files() 