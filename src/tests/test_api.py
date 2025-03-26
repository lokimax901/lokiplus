import requests
import pytest
from datetime import datetime
import json

API_URL = 'https://lokiplus-api.onrender.com'

def test_health_check():
    """Test the health check endpoint."""
    try:
        response = requests.get(f'{API_URL}/health', timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Health check response: {json.dumps(data, indent=2)}")
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
    except requests.exceptions.RequestException as e:
        print(f"Health check request failed: {str(e)}")
        raise

def test_cors_headers():
    """Test CORS headers are properly set."""
    try:
        response = requests.options(
            f'{API_URL}/health',
            headers={
                'Origin': 'https://lokiplus.netlify.app',
                'Access-Control-Request-Method': 'GET'
            },
            timeout=10
        )
        print(f"CORS headers: {json.dumps(dict(response.headers), indent=2)}")
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
        assert response.headers['Access-Control-Allow-Origin'] == 'https://lokiplus.netlify.app'
    except requests.exceptions.RequestException as e:
        print(f"CORS test request failed: {str(e)}")
        raise

def test_get_clients():
    """Test the get_clients endpoint."""
    try:
        response = requests.get(f'{API_URL}/api/clients', timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Get clients response: {json.dumps(data[:2], indent=2)}")  # Show first 2 clients only
        assert isinstance(data, list)
    except requests.exceptions.RequestException as e:
        print(f"Get clients request failed: {str(e)}")
        raise

if __name__ == '__main__':
    print("Testing API connection...")
    tests = [
        ('Health check', test_health_check),
        ('CORS headers', test_cors_headers),
        ('Get clients', test_get_clients)
    ]
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            test_func()
            print(f"✓ {test_name} test passed")
        except Exception as e:
            print(f"❌ {test_name} test failed: {str(e)}")
            break
    else:
        print("\nAll tests passed successfully!") 