import os
import shutil
from pathlib import Path

def build_static_files():
    """Build and organize static files for production."""
    # Create static directory if it doesn't exist
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    # Copy template files to static directory
    template_dir = Path('templates')
    if template_dir.exists():
        for template in template_dir.glob('*.html'):
            shutil.copy2(template, static_dir / template.name)
            print(f"Copied {template.name} to static directory")
    
    # Copy static assets
    static_src = Path('static')
    if static_src.exists():
        # Copy CSS files
        css_dir = static_dir / 'css'
        css_dir.mkdir(exist_ok=True)
        for css in static_src.glob('css/*.css'):
            shutil.copy2(css, css_dir / css.name)
            print(f"Copied {css.name} to static/css")
        
        # Copy JavaScript files
        js_dir = static_dir / 'js'
        js_dir.mkdir(exist_ok=True)
        for js in static_src.glob('js/*.js'):
            shutil.copy2(js, js_dir / js.name)
            print(f"Copied {js.name} to static/js")
        
        # Copy images
        img_dir = static_dir / 'img'
        img_dir.mkdir(exist_ok=True)
        for img in static_src.glob('img/*'):
            shutil.copy2(img, img_dir / img.name)
            print(f"Copied {img.name} to static/img")
    
    # Create a simple 404 page
    with open(static_dir / '404.html', 'w') as f:
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
    
    print("Static build completed successfully!")

if __name__ == '__main__':
    build_static_files() 