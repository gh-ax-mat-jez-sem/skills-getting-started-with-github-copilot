"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = next(iter(data.values()))
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_activities_have_correct_structure(self, client):
        """Test that each activity has the correct data structure"""
        response = client.get("/activities")
        data = response.json()
        
        for name, details in data.items():
            assert isinstance(name, str)
            assert isinstance(details["description"], str)
            assert isinstance(details["schedule"], str)
            assert isinstance(details["max_participants"], int)
            assert isinstance(details["participants"], list)


class TestSignup:
    """Tests for signing up for activities"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Remove all participants from Chess Club first
        activities["Chess Club"]["participants"] = []
        
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify student was added
        assert "test@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_when_already_registered(self, client):
        """Test that a student cannot sign up for multiple activities"""
        # Sign up for first activity
        activities["Chess Club"]["participants"] = []
        client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        
        # Try to sign up for another activity
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client):
        """Test that multiple students can sign up for the same activity"""
        activities["Chess Club"]["participants"] = []
        
        response1 = client.post(
            "/activities/Chess%20Club/signup?email=student1@mergington.edu"
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            "/activities/Chess%20Club/signup?email=student2@mergington.edu"
        )
        assert response2.status_code == 200
        
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "student1@mergington.edu" in activities["Chess Club"]["participants"]
        assert "student2@mergington.edu" in activities["Chess Club"]["participants"]


class TestUnregister:
    """Tests for unregistering from activities"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # Add a participant first
        activities["Chess Club"]["participants"] = ["test@mergington.edu"]
        
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify student was removed
        assert "test@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_when_not_registered(self, client):
        """Test unregister when student is not registered for the activity"""
        activities["Chess Club"]["participants"] = []
        
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_does_not_affect_other_participants(self, client):
        """Test that unregistering one student doesn't affect others"""
        activities["Chess Club"]["participants"] = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=student2@mergington.edu"
        )
        assert response.status_code == 200
        
        participants = activities["Chess Club"]["participants"]
        assert len(participants) == 2
        assert "student1@mergington.edu" in participants
        assert "student3@mergington.edu" in participants
        assert "student2@mergington.edu" not in participants


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_email_with_special_characters(self, client):
        """Test signup with email containing special characters"""
        activities["Chess Club"]["participants"] = []
        
        response = client.post(
            "/activities/Chess%20Club/signup?email=test%2Bspecial@mergington.edu"
        )
        assert response.status_code == 200
        assert "test+special@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_activity_name_with_spaces(self, client):
        """Test that activity names with spaces work correctly"""
        activities["Programming Class"]["participants"] = []
        
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        assert "test@mergington.edu" in activities["Programming Class"]["participants"]
