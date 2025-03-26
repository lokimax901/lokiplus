#!/bin/bash
set -e # Exit on error

echo "Starting build process..."

# Setup Python environment
echo "Setting up Python environment..."
python3.9 -m venv .venv
source .venv/bin/activate || . .venv/Scripts/activate

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p public
mkdir -p netlify/functions

# Copy static files and templates
echo "Copying static files..."
if [ -d "src/templates" ]; then
    cp -r src/templates/* public/ 2>/dev/null || true
fi

if [ -d "src/static" ]; then
    cp -r src/static/* public/ 2>/dev/null || true
fi

# Create a simple index.html that redirects to the Flask app
echo "Creating index.html..."
cat > public/index.html << EOL
<!DOCTYPE html>
<html>
<head>
    <title>SubMax</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background-color: #f8f9fa;
        }
        .loader {
            border: 4px solid #f3f3f3;
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="text-center">
        <div class="loader d-inline-block"></div>
        <p class="h4 d-inline-block">Loading SubMax...</p>
    </div>
    <script>
        window.location.href = '/admin/login';
    </script>
</body>
</html>
EOL

# Print Python and pip versions for debugging
echo "Python version:"
python --version
echo "Pip version:"
pip --version

echo "Build completed successfully!" 