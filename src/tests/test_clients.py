import pytest
from datetime import datetime, timedelta
import json

def test_get_clients_json(client, test_data):
    """Test getting clients list in JSON format"""
    response = client.get('/clients?format=json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert len(data['clients']) == 2
    assert data['clients'][0]['email'] == 'test1@example.com'
    assert data['clients'][1]['email'] == 'test2@example.com'

def test_get_clients_html(client, test_data):
    """Test getting clients list in HTML format"""
    response = client.get('/clients')
    assert response.status_code == 200
    assert b'Test Client 1' in response.data
    assert b'Test Client 2' in response.data

def test_add_client_success(client, db):
    """Test successfully adding a new client"""
    data = {
        'name': 'New Test Client',
        'email': 'newtest@example.com',
        'phone': '5555555555',
        'renewal_date': '2024-12-31'
    }
    response = client.post('/add_client', data=data)
    assert response.status_code == 302  # Redirect after success
    
    # Verify client was added
    cur = db.cursor()
    cur.execute("SELECT name, email FROM clients WHERE email = %s", ('newtest@example.com',))
    result = cur.fetchone()
    assert result is not None
    assert result[0] == 'New Test Client'

def test_add_client_duplicate_email(client, test_data):
    """Test adding a client with duplicate email"""
    data = {
        'name': 'Duplicate Client',
        'email': 'test1@example.com',  # This email already exists in test_data
        'phone': '5555555555'
    }
    response = client.post('/add_client', data=data)
    assert response.status_code == 302  # Redirects even on error
    # Could check for flash message in session if needed

def test_add_client_invalid_email(client):
    """Test adding a client with invalid email format"""
    data = {
        'name': 'Invalid Email Client',
        'email': 'not-an-email',
        'phone': '5555555555'
    }
    response = client.post('/add_client', data=data)
    assert response.status_code == 302

def test_renew_client_success(client, test_data):
    """Test successfully renewing a client"""
    client_id = test_data['client_ids'][0]
    new_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    response = client.post('/renew_client', 
                         json={
                             'client_id': client_id,
                             'renewal_date': new_date
                         },
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['renewal_date'] == new_date

def test_renew_client_invalid_date(client, test_data):
    """Test renewing a client with invalid date format"""
    client_id = test_data['client_ids'][0]
    
    response = client.post('/renew_client',
                         json={
                             'client_id': client_id,
                             'renewal_date': 'invalid-date'
                         },
                         content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False

def test_renew_client_nonexistent(client):
    """Test renewing a non-existent client"""
    response = client.post('/renew_client',
                         json={
                             'client_id': 9999,
                             'renewal_date': '2024-12-31'
                         },
                         content_type='application/json')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False

def test_check_client_exists(client, test_data):
    """Test checking if a client exists"""
    response = client.post('/check_client',
                         data={'email': 'test1@example.com'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['exists'] is True
    assert data['client']['email'] == 'test1@example.com'

def test_check_client_not_exists(client):
    """Test checking a non-existent client"""
    response = client.post('/check_client',
                         data={'email': 'nonexistent@example.com'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['exists'] is False 