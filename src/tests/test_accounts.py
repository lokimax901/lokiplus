import pytest
import json
import bcrypt

def test_add_account_success(client, db):
    """Test successfully adding a new account"""
    data = {
        'email': 'newacc@example.com',
        'password': 'Password123!',
        'status': 'active'
    }
    response = client.post('/add_account', data=data)
    assert response.status_code == 302  # Redirect after success
    
    # Verify account was added
    cur = db.cursor()
    cur.execute("SELECT email, status FROM accounts WHERE email = %s", ('newacc@example.com',))
    result = cur.fetchone()
    assert result is not None
    assert result[0] == 'newacc@example.com'
    assert result[1] == 'active'

def test_add_account_duplicate_email(client, test_data):
    """Test adding an account with duplicate email"""
    data = {
        'email': 'account1@example.com',  # This email already exists in test_data
        'password': 'Password123!',
        'status': 'active'
    }
    response = client.post('/add_account', data=data)
    assert response.status_code == 302  # Redirects even on error

def test_add_account_weak_password(client):
    """Test adding an account with a weak password"""
    data = {
        'email': 'weak@example.com',
        'password': 'weak',  # Too short, no numbers, no uppercase
        'status': 'active'
    }
    response = client.post('/add_account', data=data)
    assert response.status_code == 302  # Redirects with error

def test_update_status_success(client, test_data):
    """Test successfully updating account status"""
    account_id = test_data['account_ids'][0]
    data = {
        'account_id': account_id,
        'status': 'inactive'
    }
    response = client.post('/update_status', data=data)
    assert response.status_code == 302  # Redirect after success
    
    # Verify status was updated
    cur = client.application.test_client().application.config['db'].cursor()
    cur.execute("SELECT status FROM accounts WHERE id = %s", (account_id,))
    result = cur.fetchone()
    assert result[0] == 'inactive'

def test_update_status_invalid_account(client):
    """Test updating status for non-existent account"""
    data = {
        'account_id': 9999,
        'status': 'inactive'
    }
    response = client.post('/update_status', data=data)
    assert response.status_code == 302  # Redirects with error

def test_get_account_clients_success(client, test_data):
    """Test getting clients for an account"""
    account_id = test_data['account_ids'][0]
    response = client.get(f'/account_clients/{account_id}')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'clients' in data
    assert len(data['clients']) == 1
    assert data['clients'][0]['email'] == 'test1@example.com'

def test_get_account_clients_no_clients(client, test_data):
    """Test getting clients for an account with no clients"""
    account_id = test_data['account_ids'][1]  # This account has no linked clients
    response = client.get(f'/account_clients/{account_id}')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'clients' in data
    assert len(data['clients']) == 0

def test_get_account_clients_invalid_account(client):
    """Test getting clients for non-existent account"""
    response = client.get('/account_clients/9999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_delete_account_success(client, test_data, db):
    """Test successfully deleting an account"""
    account_id = test_data['account_ids'][0]
    response = client.post('/delete_account', data={'account_id': account_id})
    assert response.status_code == 302  # Redirect after success
    
    # Verify account was deleted
    cur = db.cursor()
    cur.execute("SELECT id FROM accounts WHERE id = %s", (account_id,))
    result = cur.fetchone()
    assert result is None
    
    # Verify client_accounts were deleted
    cur.execute("SELECT id FROM client_accounts WHERE account_id = %s", (account_id,))
    result = cur.fetchone()
    assert result is None

def test_delete_account_nonexistent(client):
    """Test deleting non-existent account"""
    response = client.post('/delete_account', data={'account_id': 9999})
    assert response.status_code == 302  # Redirects with error 