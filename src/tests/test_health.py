import pytest
import json
from datetime import datetime, timedelta

def test_health_endpoint(client):
    """Test the main health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert 'timestamp' in data
    assert 'details' in data
    assert isinstance(data['details'], dict)

def test_database_health_endpoint(client):
    """Test the database health check endpoint"""
    response = client.get('/health/database')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert 'timestamp' in data
    assert 'details' in data
    assert 'tables' in data['details']
    assert 'connection_status' in data['details']

def test_database_health_force_check(client):
    """Test forcing a database health check"""
    response = client.get('/health/database?force=true')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['details']['force_checked'] is True

def test_routes_health_endpoint(client, test_data):
    """Test the routes health check endpoint"""
    # First make some requests to generate route statistics
    client.get('/clients')
    client.get('/health')
    
    response = client.get('/health/routes')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'routes' in data
    assert isinstance(data['routes'], list)
    assert len(data['routes']) > 0
    
    # Check route statistics format
    route = data['routes'][0]
    assert 'path' in route
    assert 'method' in route
    assert 'hits' in route
    assert 'avg_response_time' in route
    assert 'error_rate' in route

def test_recommendations_endpoint(client):
    """Test the health recommendations endpoint"""
    response = client.get('/health/recommendations')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'recommendations' in data
    assert isinstance(data['recommendations'], list)

def test_health_check_with_db_error(client, db):
    """Test health check when database connection fails"""
    # Close the database connection to simulate an error
    db.close()
    
    response = client.get('/health/database')
    assert response.status_code == 200  # Should still return 200 but with error status
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'connection_error' in data['details']

def test_route_monitoring(client):
    """Test route monitoring functionality"""
    # Make multiple requests to a route
    for _ in range(3):
        client.get('/clients')
    
    response = client.get('/health/routes')
    data = json.loads(response.data)
    
    # Find the /clients route statistics
    clients_route = next(r for r in data['routes'] if r['path'] == '/clients')
    assert clients_route['hits'] >= 3
    assert clients_route['avg_response_time'] > 0
    assert 'error_rate' in clients_route

def test_error_monitoring(client):
    """Test error monitoring in health checks"""
    # Trigger a 404 error
    client.get('/nonexistent-route')
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert 'error_rates' in data['details']
    assert data['details']['error_rates']['4xx'] > 0

def test_cache_behavior(client):
    """Test health check caching behavior"""
    # Make two quick requests
    response1 = client.get('/health/database')
    response2 = client.get('/health/database')
    
    data1 = json.loads(response1.data)
    data2 = json.loads(response2.data)
    
    # Should return cached data
    assert data1['timestamp'] == data2['timestamp']
    
    # Force refresh should bypass cache
    response3 = client.get('/health/database?force=true')
    data3 = json.loads(response3.data)
    assert data3['timestamp'] != data1['timestamp'] 