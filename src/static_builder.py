import os
from flask import Flask, render_template
from flask.testing import FlaskClient
from app import app, supabase
import shutil
from pathlib import Path
from datetime import datetime

def get_mock_data():
    """Get mock data for static site generation"""
    mock_data = {
        'accounts': [],
        'clients': [],
        'db_error': None,
        'error': None,
        'message': None
    }
    
    try:
        # Try to get real data from Supabase
        accounts_response = supabase.table('accounts').select('*').execute()
        clients_response = supabase.table('clients').select('*').execute()
        
        mock_data['accounts'] = accounts_response.data
        mock_data['clients'] = clients_response.data
        
        # Get client count for each account
        for account in mock_data['accounts']:
            count_result = supabase.table('account_clients').select(
                'id', count='exact'
            ).eq('account_id', account['id']).execute()
            account['client_count'] = count_result.count or 0
            
            # Format the created_at date
            if account.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(account['created_at'].replace('Z', '+00:00'))
                    account['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    account['created_at'] = account['created_at']
    except Exception as e:
        print(f"Warning: Could not fetch real data, using empty mock data: {e}")
        mock_data['db_error'] = True
    
    return mock_data

def create_static_site():
    """Convert Flask templates to static HTML"""
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
    
    # Get mock data for template rendering
    mock_data = get_mock_data()
    
    # Generate static HTML
    with app.app_context():
        # Render index template with mock data
        index_html = render_template(
            'index.html',
            accounts=mock_data['accounts'],
            clients=mock_data['clients'],
            db_error=mock_data['db_error'],
            error=mock_data['error']
        )
        
        # Fix static asset paths
        index_html = index_html.replace("{{ url_for('static',", "/static/")
        index_html = index_html.replace("{{ url_for('","/")
        index_html = index_html.replace("') }}", "")
        index_html = index_html.replace(") }}", "")
        
        # Write the rendered HTML
        with open(build_dir / "index.html", "w", encoding='utf-8') as f:
            f.write(index_html)
        
        print("Static site generated successfully!")

if __name__ == "__main__":
    create_static_site() 