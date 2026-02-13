# Complete Testing Guide for KeyShift

## Table of Contents
1. [Testing Strategy Overview](#testing-strategy-overview)
2. [Setting Up Your Testing Environment](#setting-up-your-testing-environment)
3. [Project Structure for Tests](#project-structure-for-tests)
4. [Unit Testing](#unit-testing)
5. [Integration Testing](#integration-testing)
6. [API Testing](#api-testing)
7. [End-to-End Testing](#end-to-end-testing)
8. [Test Coverage](#test-coverage)
9. [Running Tests in CI/CD](#running-tests-in-cicd)
10. [Best Practices](#best-practices)

---

## Testing Strategy Overview

### Testing Pyramid for KeyShift

```
         /\
        /E2E\         Few tests, test full user flows
       /------\
      /  API   \      Medium amount, test API endpoints
     /----------\
    / Integration\    More tests, test component interaction
   /--------------\
  /  Unit Tests   \   Most tests, test individual functions
 /----------------\
```

**Target Coverage:**
- Unit Tests: 80%+ coverage
- Integration Tests: Key workflows
- API Tests: All endpoints
- E2E Tests: Critical user journeys

---

## Setting Up Your Testing Environment

### 1. Install Testing Dependencies

Create `requirements-dev.txt`:

```txt
# Testing Framework
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0
pytest-mock==3.12.0

# Test Database
testing.postgresql==1.3.0

# Fixtures and Factories
factory-boy==3.3.0
faker==20.1.0

# HTTP Mocking
responses==0.24.1
requests-mock==1.11.0

# Code Quality
black==23.12.0
flake8==6.1.0
mypy==1.7.1
pylint==3.0.3

# Coverage Reporting
coverage[toml]==7.3.3
```

Install:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Create Test Configuration

Create `tests/conftest.py`:

```python
"""
Pytest configuration and shared fixtures.
"""
import pytest
import os
import tempfile
from app import create_app, db
from app.models import user, SSID

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Set test config
    os.environ['TESTING'] = 'true'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['WTF_CSRF_ENABLED'] = 'false'  # Disable CSRF for testing
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
    })
    
    # Create database
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Create clean database session for each test."""
    with app.app_context():
        # Clean all tables
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield db.session
        db.session.remove()

@pytest.fixture
def auth_client(client, db_session):
    """Create authenticated test client."""
    # Create test user
    test_user = user.newUser('testuser', 'TestPass123!', True)
    
    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'TestPass123!'
    })
    
    return client

@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    test_user = user(
        username='testuser',
        password=b'$2b$12$test.hash.here',
        admin=False,
        active=True,
        apiKey='test-api-key'
    )
    db.session.add(test_user)
    db.session.commit()
    return test_user

@pytest.fixture
def sample_ssid(db_session):
    """Create a sample SSID for testing."""
    test_ssid = SSID(
        ssidName='TestNetwork',
        ssidPW='TestPassword123',
        siteID='test-site-id',
        wlanGroupID='test-wlan-group',
        ssidID='test-ssid-id',
        status=True,
        pwRotate=False,
        qrCode=False,
        isGuest=False
    )
    db.session.add(test_ssid)
    db.session.commit()
    return test_ssid

@pytest.fixture
def mock_unifi_api(monkeypatch):
    """Mock UniFi API responses."""
    import responses
    
    @responses.activate
    def _mock():
        # Mock successful password change
        responses.add(
            responses.GET,
            'https://192.168.1.1/proxy/network/integration/v1/sites/test-site/wifi/broadcasts/test-ssid',
            json={
                'id': 'test-ssid',
                'name': 'TestNetwork',
                'securityConfiguration': {'passphrase': 'OldPassword'},
                'metadata': {}
            },
            status=200
        )
        
        responses.add(
            responses.PUT,
            'https://192.168.1.1/proxy/network/integration/v1/sites/test-site/wifi/broadcasts/test-ssid',
            json={'success': True},
            status=200
        )
        
        return responses
    
    return _mock
```

---

## Project Structure for Tests

Create this directory structure:

```
tests/
├── conftest.py              # Shared fixtures
├── __init__.py
│
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_utilities.py
│   └── test_config.py
│
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_routes.py
│   ├── test_auth.py
│   └── test_api_clients.py
│
├── api/                     # API endpoint tests
│   ├── __init__.py
│   ├── test_admin_api.py
│   └── test_ssid_api.py
│
├── e2e/                     # End-to-end tests
│   ├── __init__.py
│   └── test_user_workflows.py
│
└── fixtures/                # Test data
    ├── __init__.py
    ├── factories.py
    └── mock_data.py
```

---

## Unit Testing

### Test Models (tests/unit/test_models.py)

```python
"""
Unit tests for database models.
"""
import pytest
from flask_bcrypt import bcrypt
from app.models import user, SSID

class TestUserModel:
    """Tests for the User model."""
    
    def test_create_user(self, db_session):
        """Test creating a new user."""
        result = user.newUser('john_doe', 'SecurePass123!', True)
        
        assert 'has been added' in result
        created_user = user.query.filter_by(username='john_doe').first()
        assert created_user is not None
        assert created_user.admin == True
        assert created_user.active == True
        assert created_user.apiKey is not None
    
    def test_password_hashing(self, db_session):
        """Test that passwords are properly hashed."""
        password = 'MyPassword123!'
        user.newUser('test_user', password, False)
        
        created_user = user.query.filter_by(username='test_user').first()
        
        # Password should be hashed
        assert created_user.password != password.encode('utf-8')
        
        # Should be able to verify password
        assert bcrypt.checkpw(password.encode('utf-8'), created_user.password)
    
    def test_user_repr(self, sample_user):
        """Test user string representation."""
        assert 'Username: testuser' in str(sample_user)
    
    def test_duplicate_username(self, db_session):
        """Test that duplicate usernames are handled."""
        user.newUser('duplicate', 'Pass123!', False)
        
        # Attempting to create duplicate should raise an error
        with pytest.raises(Exception):
            user.newUser('duplicate', 'Pass123!', False)

class TestSSIDModel:
    """Tests for the SSID model."""
    
    def test_create_ssid(self, db_session):
        """Test creating a new SSID."""
        result = SSID.newSSID(
            ssidName='TestWiFi',
            ssidPW='TestPass123',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-1',
            status=True
        )
        
        assert 'has been added' in result
        created_ssid = SSID.query.filter_by(ssidName='TestWiFi').first()
        assert created_ssid is not None
        assert created_ssid.status == True
        assert created_ssid.isGuest == False
    
    def test_make_guest_no_existing_guest(self, sample_ssid):
        """Test making an SSID a guest network when none exists."""
        result = sample_ssid.makeGuest()
        
        assert 'is now the guest SSID' in result
        assert sample_ssid.isGuest == True
    
    def test_make_guest_with_existing_guest(self, db_session):
        """Test making an SSID guest when another is already guest."""
        # Create two SSIDs
        ssid1 = SSID(
            ssidName='Network1',
            ssidPW='Pass1',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-1',
            isGuest=True
        )
        ssid2 = SSID(
            ssidName='Network2',
            ssidPW='Pass2',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-2',
            isGuest=False
        )
        db_session.add(ssid1)
        db_session.add(ssid2)
        db_session.commit()
        
        # Make ssid2 the guest
        ssid2.makeGuest()
        
        db_session.refresh(ssid1)
        db_session.refresh(ssid2)
        
        assert ssid1.isGuest == False
        assert ssid2.isGuest == True
    
    def test_add_rotation_enable(self, sample_ssid):
        """Test enabling password rotation."""
        result = sample_ssid.addRotation('@daily')
        
        assert 'rotation added' in result
        assert sample_ssid.pwRotate == True
        assert sample_ssid.rotateFrequency == '@daily'
    
    def test_add_rotation_disable(self, sample_ssid):
        """Test disabling password rotation."""
        # First enable it
        sample_ssid.addRotation('@daily')
        
        # Then disable
        result = sample_ssid.addRotation(None)
        
        assert 'rotation removed' in result
        assert sample_ssid.pwRotate == False
        assert sample_ssid.rotateFrequency is None
    
    def test_ssid_repr(self, sample_ssid):
        """Test SSID string representation."""
        repr_str = str(sample_ssid)
        assert 'TestNetwork' in repr_str
        assert 'test-site-id' in repr_str
```

### Test Utilities (tests/unit/test_utilities.py)

```python
"""
Unit tests for utility functions.
"""
import pytest
import string
from app.utilities.genPW import genPW
from app.utilities.genQR import genQRCode

class TestPasswordGeneration:
    """Tests for password generation utility."""
    
    def test_default_password_length(self):
        """Test that default password length is 40."""
        password = genPW()
        assert len(password) == 40
    
    def test_custom_password_length(self):
        """Test generating password with custom length."""
        password = genPW(length=20)
        assert len(password) == 20
    
    def test_password_complexity(self):
        """Test that generated password meets complexity requirements."""
        password = genPW()
        
        # Must have lowercase
        assert any(c.islower() for c in password)
        
        # Must have uppercase
        assert any(c.isupper() for c in password)
        
        # Must have digit
        assert any(c.isdigit() for c in password)
        
        # Must have punctuation
        assert any(c in string.punctuation for c in password)
    
    def test_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [genPW() for _ in range(100)]
        
        # All passwords should be unique
        assert len(passwords) == len(set(passwords))
    
    def test_password_characters(self):
        """Test that password only contains valid characters."""
        password = genPW()
        valid_chars = string.ascii_letters + string.digits + string.punctuation
        
        for char in password:
            assert char in valid_chars

class TestQRCodeGeneration:
    """Tests for QR code generation utility."""
    
    def test_generate_qr_code(self, sample_ssid, tmp_path, monkeypatch):
        """Test generating QR code for SSID."""
        # Mock the static directory
        monkeypatch.setattr('app.utilities.genQR.Path', lambda x: tmp_path / x)
        
        result = genQRCode(sample_ssid)
        
        # Check that function succeeded
        assert result is not None
    
    def test_qr_code_format(self, sample_ssid):
        """Test that QR code contains correct WiFi format."""
        # This would test the WIFI:T:WPA;S:SSID;P:password;; format
        # Implementation depends on your genQRCode function
        pass
```

### Test Configuration (tests/unit/test_config.py)

```python
"""
Unit tests for configuration management.
"""
import pytest
import os
import json
from app.config.config import getConfig, updateConfig

class TestConfiguration:
    """Tests for configuration functions."""
    
    def test_get_config_from_env(self, monkeypatch):
        """Test getting configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv('CONTROLLER_IP', '192.168.1.100')
        monkeypatch.setenv('API_TYPE', 'omada')
        monkeypatch.setenv('OMADA_USERNAME', 'admin')
        
        config = getConfig()
        
        assert config['controllerIp'] == '192.168.1.100'
        assert config['apiType'] == 'omada'
        assert config['apiUser']['userName'] == 'admin'
    
    def test_get_config_defaults(self, monkeypatch):
        """Test configuration defaults when env vars not set."""
        # Clear relevant env vars
        monkeypatch.delenv('CONTROLLER_IP', raising=False)
        monkeypatch.delenv('API_TYPE', raising=False)
        
        config = getConfig()
        
        # Should have defaults
        assert 'controllerIp' in config
        assert 'apiType' in config
    
    def test_update_config(self, tmp_path, monkeypatch):
        """Test updating configuration."""
        config_file = tmp_path / "config.json"
        monkeypatch.setattr('app.config.config.filename', str(config_file))
        
        new_config = {
            'apiType': 'unifi',
            'controllerIp': '192.168.1.50'
        }
        
        result = updateConfig(new_config)
        
        assert 'Successfully updated' in result
        
        # Verify file was written
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config['apiType'] == 'unifi'
```

---

## Integration Testing

### Test Routes (tests/integration/test_routes.py)

```python
"""
Integration tests for application routes.
"""
import pytest
from flask import session

class TestGuestRoutes:
    """Tests for guest-facing routes."""
    
    def test_guest_page_no_users(self, client, db_session):
        """Test guest page redirects to init when no users exist."""
        response = client.get('/')
        
        assert response.status_code == 302
        assert '/initApp' in response.location
    
    def test_guest_page_with_guest_ssid(self, client, db_session, sample_user, sample_ssid):
        """Test guest page displays guest SSID."""
        # Make SSID a guest network
        sample_ssid.makeGuest()
        db_session.commit()
        
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'TestNetwork' in response.data
        assert b'TestPassword123' in response.data
    
    def test_guest_page_no_guest_ssid(self, client, db_session, sample_user, sample_ssid):
        """Test guest page when no guest SSID exists."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'No Guest SSID Found' in response.data

class TestAuthenticationRoutes:
    """Tests for authentication routes."""
    
    def test_login_page_loads(self, client, sample_user):
        """Test login page loads successfully."""
        response = client.get('/login')
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_login_success(self, client, db_session):
        """Test successful login."""
        # Create user with known password
        from flask_bcrypt import bcrypt
        salt = bcrypt.gensalt()
        hashed_pw = bcrypt.hashpw('TestPass123!'.encode('utf-8'), salt)
        
        from app.models import user as User
        test_user = User(
            username='logintest',
            password=hashed_pw,
            admin=True,
            active=True,
            apiKey='test-key'
        )
        db_session.add(test_user)
        db_session.commit()
        
        response = client.post('/login', data={
            'username': 'logintest',
            'password': 'TestPass123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'admin' in response.data.lower()
    
    def test_login_failure_wrong_password(self, client, db_session, sample_user):
        """Test login fails with wrong password."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'WrongPassword'
        })
        
        assert b'Incorrect Username or Password' in response.data
    
    def test_login_failure_nonexistent_user(self, client, db_session):
        """Test login fails with nonexistent user."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password'
        })
        
        assert b'Incorrect Username or Password' in response.data
    
    def test_logout(self, auth_client):
        """Test logout functionality."""
        response = auth_client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_protected_route_requires_auth(self, client):
        """Test that protected routes require authentication."""
        response = client.get('/admin')
        
        assert response.status_code == 302
        assert '/login' in response.location

class TestAdminRoutes:
    """Tests for admin routes."""
    
    def test_admin_page_requires_auth(self, client):
        """Test admin page requires authentication."""
        response = client.get('/admin')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_admin_page_loads_for_authenticated(self, auth_client, sample_ssid):
        """Test admin page loads for authenticated users."""
        response = auth_client.get('/admin')
        
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_admin_page_displays_ssids(self, auth_client, sample_ssid):
        """Test admin page displays SSID information."""
        response = auth_client.get('/admin')
        
        assert response.status_code == 200
        assert b'TestNetwork' in response.data
    
    def test_change_config(self, auth_client, db_session):
        """Test updating configuration."""
        response = auth_client.post('/updateConfig', data={
            'api_type': 'omada',
            'username': 'newuser',
            'password': 'newpass',
            'controller_host': '192.168.1.100',
            'tab': 'configuration'
        })
        
        assert response.status_code == 302
        assert 'tab=configuration' in response.location

class TestSSIDManagement:
    """Tests for SSID management routes."""
    
    def test_change_password_requires_auth(self, client, sample_ssid):
        """Test password change requires authentication."""
        response = client.get(f'/changepw/{sample_ssid.id}')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_make_guest_requires_auth(self, client, sample_ssid):
        """Test make guest requires authentication."""
        response = client.get(f'/makeguest/{sample_ssid.id}')
        
        assert response.status_code == 302
    
    def test_create_cron_job(self, auth_client, sample_ssid):
        """Test creating cron job for SSID."""
        response = auth_client.get(
            f'/createCron/{sample_ssid.id}?rotateFrequency=@daily'
        )
        
        # Should redirect back
        assert response.status_code == 302
        
        # Verify SSID was updated
        from app.models import SSID
        updated_ssid = SSID.query.get(sample_ssid.id)
        assert updated_ssid.pwRotate == True
        assert updated_ssid.rotateFrequency == '@daily'
    
    def test_delete_cron_job(self, auth_client, db_session):
        """Test deleting cron job for SSID."""
        # Create SSID with rotation enabled
        from app.models import SSID
        ssid = SSID(
            ssidName='CronTest',
            ssidPW='Pass123',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-cron',
            pwRotate=True,
            rotateFrequency='@daily'
        )
        db_session.add(ssid)
        db_session.commit()
        
        response = auth_client.get(
            f'/createCron/{ssid.id}?rotateFrequency=None'
        )
        
        assert response.status_code == 302
        
        # Verify rotation was disabled
        updated_ssid = SSID.query.get(ssid.id)
        assert updated_ssid.pwRotate == False

class TestUserManagement:
    """Tests for user management routes."""
    
    def test_add_user_requires_auth(self, client):
        """Test adding user requires authentication."""
        response = client.post('/users/add', data={
            'newUsername': 'newuser',
            'newPassword': 'Pass123!',
            'newPasswordConfirm': 'Pass123!',
            'newRole': 'user'
        })
        
        assert response.status_code == 401
    
    def test_add_user_success(self, auth_client, db_session):
        """Test successfully adding a new user."""
        response = auth_client.post('/users/add', data={
            'newUsername': 'newuser',
            'newPassword': 'Pass123!',
            'newPasswordConfirm': 'Pass123!',
            'newRole': 'user'
        })
        
        assert response.status_code == 302
        
        # Verify user was created
        from app.models import user
        new_user = user.query.filter_by(username='newuser').first()
        assert new_user is not None
        assert new_user.admin == False
    
    def test_add_user_password_mismatch(self, auth_client, db_session):
        """Test adding user fails with password mismatch."""
        response = auth_client.post('/users/add', data={
            'newUsername': 'baduser',
            'newPassword': 'Pass123!',
            'newPasswordConfirm': 'DifferentPass',
            'newRole': 'user'
        })
        
        # Should redirect back to admin
        assert response.status_code == 302
        
        # User should not exist
        from app.models import user
        bad_user = user.query.filter_by(username='baduser').first()
        assert bad_user is None
```

### Test API Clients (tests/integration/test_api_clients.py)

```python
"""
Integration tests for API clients.
"""
import pytest
import responses
from app.api.unifi import UNIFI
from app.models import SSID

class TestUniFiAPI:
    """Tests for UniFi API client."""
    
    @responses.activate
    def test_get_site_ids(self, monkeypatch):
        """Test fetching site IDs from UniFi."""
        # Mock environment
        monkeypatch.setenv('CONTROLLER_IP', '192.168.1.1')
        monkeypatch.setenv('UNIFI_API_KEY', 'test-key')
        
        # Mock API response
        responses.add(
            responses.GET,
            'https://192.168.1.1/proxy/network/integration/v1/sites',
            json={
                'data': [
                    {'id': 'site-1'},
                    {'id': 'site-2'}
                ]
            },
            status=200
        )
        
        site_ids = UNIFI.getSiteIDs()
        
        assert len(site_ids) == 2
        assert 'site-1' in site_ids
        assert 'site-2' in site_ids
    
    @responses.activate
    def test_change_password_success(self, sample_ssid, monkeypatch):
        """Test successfully changing WiFi password via UniFi API."""
        # Mock environment
        monkeypatch.setenv('CONTROLLER_IP', '192.168.1.1')
        monkeypatch.setenv('UNIFI_API_KEY', 'test-key')
        
        # Mock GET request
        responses.add(
            responses.GET,
            f'https://192.168.1.1/proxy/network/integration/v1/sites/{sample_ssid.siteID}/wifi/broadcasts/{sample_ssid.ssidID}',
            json={
                'id': sample_ssid.ssidID,
                'name': sample_ssid.ssidName,
                'securityConfiguration': {'passphrase': 'OldPassword'},
                'metadata': {}
            },
            status=200
        )
        
        # Mock PUT request
        responses.add(
            responses.PUT,
            f'https://192.168.1.1/proxy/network/integration/v1/sites/{sample_ssid.siteID}/wifi/broadcasts/{sample_ssid.ssidID}',
            json={'success': True},
            status=200
        )
        
        result = UNIFI.changePW(sample_ssid, 'NewPassword123')
        
        assert result == True
    
    @responses.activate
    def test_change_password_failure(self, sample_ssid, monkeypatch):
        """Test handling API failure when changing password."""
        monkeypatch.setenv('CONTROLLER_IP', '192.168.1.1')
        monkeypatch.setenv('UNIFI_API_KEY', 'test-key')
        
        # Mock GET succeeds
        responses.add(
            responses.GET,
            f'https://192.168.1.1/proxy/network/integration/v1/sites/{sample_ssid.siteID}/wifi/broadcasts/{sample_ssid.ssidID}',
            json={
                'id': sample_ssid.ssidID,
                'name': sample_ssid.ssidName,
                'securityConfiguration': {'passphrase': 'OldPassword'},
                'metadata': {}
            },
            status=200
        )
        
        # Mock PUT fails
        responses.add(
            responses.PUT,
            f'https://192.168.1.1/proxy/network/integration/v1/sites/{sample_ssid.siteID}/wifi/broadcasts/{sample_ssid.ssidID}',
            json={'error': 'Unauthorized'},
            status=401
        )
        
        result = UNIFI.changePW(sample_ssid, 'NewPassword123')
        
        assert result != True
        assert 'Error' in result
```

---

## API Testing

### Test Admin API (tests/api/test_admin_api.py)

```python
"""
API endpoint tests for admin functionality.
"""
import pytest
import json

class TestAdminAPI:
    """Tests for admin API endpoints."""
    
    def test_log_action_requires_auth(self, client):
        """Test log endpoint requires authentication."""
        response = client.post('/log', 
            data=json.dumps({'message': 'test'}),
            content_type='application/json'
        )
        
        assert response.status_code == 302
    
    def test_log_action_success(self, auth_client):
        """Test logging action via API."""
        response = auth_client.post('/log',
            data=json.dumps({'message': 'Test action'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'logged successfully' in data['message']
    
    def test_init_db_requires_auth(self, client):
        """Test DB initialization requires auth."""
        response = client.get('/init')
        
        assert response.status_code == 401
    
    def test_init_db_success(self, auth_client, monkeypatch):
        """Test database initialization."""
        # Mock API calls
        def mock_init():
            return [{'ssid': 'test'}]
        
        monkeypatch.setattr('app.api.unifi.UNIFI.initDBinfo', mock_init)
        
        response = auth_client.get('/init')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Success'
```

---

## End-to-End Testing

### Test User Workflows (tests/e2e/test_user_workflows.py)

```python
"""
End-to-end tests for complete user workflows.
"""
import pytest

class TestInitialSetup:
    """Test complete initial setup workflow."""
    
    def test_complete_initialization_flow(self, client, db_session):
        """Test full app initialization from scratch."""
        # 1. Access app for first time - should redirect to init
        response = client.get('/', follow_redirects=True)
        assert b'initApp' in response.request.path.encode()
        
        # 2. Create first admin user
        response = client.post('/users/add', data={
            'newUsername': 'admin',
            'newPassword': 'SecurePass123!',
            'newPasswordConfirm': 'SecurePass123!',
            'newRole': 'admin'
        })
        assert response.status_code == 200
        
        # 3. Configure API settings
        response = client.post('/newConfig', data={
            'api_type': 'unifi',
            'controllerApiKey': 'test-key',
            'controllerIp': '192.168.1.1'
        })
        assert response.status_code == 200
        
        # 4. Initialize database (would need to mock API)
        # response = client.get('/init')
        # assert response.status_code == 200

class TestPasswordRotationWorkflow:
    """Test complete password rotation workflow."""
    
    def test_enable_and_rotate_password(self, auth_client, sample_ssid, monkeypatch):
        """Test enabling rotation and rotating password."""
        # Mock API
        def mock_change_pw(ssid, pw):
            return True
        
        monkeypatch.setattr('app.api.unifi.UNIFI.changePW', mock_change_pw)
        
        # 1. Enable rotation
        response = auth_client.get(
            f'/createCron/{sample_ssid.id}?rotateFrequency=@daily'
        )
        assert response.status_code == 302
        
        # 2. Manually change password
        response = auth_client.get(f'/changepw/{sample_ssid.id}')
        assert response.status_code == 302
        
        # 3. Verify password was changed
        from app.models import SSID
        updated_ssid = SSID.query.get(sample_ssid.id)
        assert updated_ssid.ssidPW != 'TestPassword123'

class TestGuestNetworkManagement:
    """Test guest network management workflow."""
    
    def test_set_and_view_guest_network(self, auth_client, db_session):
        """Test setting guest network and viewing it."""
        # Create multiple SSIDs
        from app.models import SSID
        ssid1 = SSID(
            ssidName='Private',
            ssidPW='PrivatePass',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-1'
        )
        ssid2 = SSID(
            ssidName='Guest',
            ssidPW='GuestPass',
            siteID='site-1',
            wlanGroupID='wlan-1',
            ssidID='ssid-2'
        )
        db_session.add(ssid1)
        db_session.add(ssid2)
        db_session.commit()
        
        # 1. Make ssid2 the guest network
        response = auth_client.get(f'/makeguest/{ssid2.id}')
        assert response.status_code == 302
        
        # 2. Verify it shows on guest page
        response = auth_client.get('/')
        assert b'Guest' in response.data
        assert b'GuestPass' in response.data
        
        # 3. Switch to ssid1 as guest
        response = auth_client.get(f'/makeguest/{ssid1.id}')
        assert response.status_code == 302
        
        # 4. Verify guest page updated
        response = auth_client.get('/')
        assert b'Private' in response.data
        assert b'PrivatePass' in response.data
```

---

## Test Coverage

### Setup Coverage Configuration

Create `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]

[tool.coverage.html]
directory = "htmlcov"
```

### Run Tests with Coverage

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_models.py -v

# Run with coverage and generate report
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

```
Name                        Stmts   Miss  Cover
-----------------------------------------------
app/__init__.py                30      2    93%
app/models.py                  85      8    91%
app/pages.py                  200     20    90%
app/utilities/genPW.py         20      1    95%
app/api/unifi.py              100     15    85%
-----------------------------------------------
TOTAL                         435     46    89%
```

Target: **80%+ overall coverage**

---

## Running Tests in CI/CD

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests with coverage
      run: |
        pytest --cov=app --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
    
    - name: Check coverage threshold
      run: |
        coverage report --fail-under=80
```

---

## Best Practices

### 1. Test Organization

✅ **DO:**
- One test class per model/view/function
- Clear, descriptive test names
- Group related tests
- Use fixtures for common setup

❌ **DON'T:**
- Mix unit and integration tests
- Have tests depend on each other
- Test multiple things in one test

### 2. Test Independence

```python
# ✅ GOOD - Each test is independent
def test_create_user(db_session):
    user = create_user('john')
    assert user.username == 'john'

def test_delete_user(db_session):
    user = create_user('jane')
    delete_user(user.id)
    assert get_user(user.id) is None

# ❌ BAD - Tests depend on each other
user_id = None

def test_create_user():
    global user_id
    user = create_user('john')
    user_id = user.id

def test_delete_user():
    delete_user(user_id)  # Depends on previous test
```

### 3. Use Descriptive Names

```python
# ✅ GOOD
def test_login_fails_with_wrong_password():
    pass

def test_password_rotation_updates_cron_schedule():
    pass

# ❌ BAD
def test_login():
    pass

def test_rotation():
    pass
```

### 4. Test Edge Cases

```python
def test_generate_password():
    # Test normal case
    pw = genPW(40)
    assert len(pw) == 40
    
    # Test edge cases
    assert len(genPW(1)) == 1
    assert len(genPW(1000)) == 1000
    
    # Test error cases
    with pytest.raises(ValueError):
        genPW(-1)
```

### 5. Mock External Dependencies

```python
# ✅ GOOD - Mock API calls
@responses.activate
def test_change_password():
    responses.add(responses.PUT, 'https://api...', status=200)
    result = change_password('new_pass')
    assert result == True

# ❌ BAD - Make real API calls in tests
def test_change_password():
    result = change_password('new_pass')  # Hits real API!
```

### 6. Use Fixtures Wisely

```python
# ✅ GOOD - Reusable fixtures
@pytest.fixture
def authenticated_user(client, db_session):
    user = create_user('test', 'pass')
    client.post('/login', data={'username': 'test', 'password': 'pass'})
    return user

def test_admin_page(client, authenticated_user):
    response = client.get('/admin')
    assert response.status_code == 200

# ❌ BAD - Repeating setup in every test
def test_admin_page(client):
    user = create_user('test', 'pass')
    client.post('/login', ...)
    response = client.get('/admin')
```

### 7. Assert Meaningful Things

```python
# ✅ GOOD
def test_password_hashing():
    user = create_user('john', 'secret')
    assert user.password != 'secret'
    assert bcrypt.verify('secret', user.password)

# ❌ BAD
def test_password_hashing():
    user = create_user('john', 'secret')
    assert user is not None  # Too vague
```

---

## Quick Start Testing Checklist

- [ ] Install testing dependencies
- [ ] Create test directory structure
- [ ] Set up conftest.py with fixtures
- [ ] Write unit tests for models
- [ ] Write unit tests for utilities
- [ ] Write integration tests for routes
- [ ] Write API tests for endpoints
- [ ] Set up coverage reporting
- [ ] Add CI/CD pipeline
- [ ] Document testing procedures
- [ ] Achieve 80%+ coverage

---

## Common Testing Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestUserModel::test_create_user

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app

# Run and stop at first failure
pytest -x

# Run only failed tests from last run
pytest --lf

# Run tests matching keyword
pytest -k "password"

# Run with print statements
pytest -s

# Run parallel (requires pytest-xdist)
pytest -n 4
```

---

## Troubleshooting

### Tests Can't Import App Modules

```python
# Add to conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Database Conflicts

```python
# Use separate test database
@pytest.fixture(scope='function')
def db_session(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db.session
        db.session.remove()
```

### Fixtures Not Found

```python
# Make sure conftest.py is in tests/ directory
# Check fixture scope (function, class, module, session)
```

---

## Next Steps

1. Start with unit tests for models and utilities
2. Add integration tests for critical routes
3. Mock external API calls
4. Measure and improve coverage
5. Add E2E tests for key workflows
6. Set up continuous testing in CI/CD

**Happy Testing! 🧪**
