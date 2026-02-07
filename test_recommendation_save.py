#!/usr/bin/env python3
"""
Test script for the recommendation field save feature.

This script tests:
1. Creating a threat
2. Updating the threat with a recommendation
3. Verifying the recommendation was saved
"""

import requests
import json
import sys
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test data - replace with your actual IDs
TENANT_ID = "00000000-0000-0000-0000-000000000001"  # Replace with actual tenant ID
USER_ID = "00000000-0000-0000-0000-000000000001"    # Replace with actual user ID
ASSESSMENT_ID = None  # Will be created or you can specify an existing one

# Headers
headers = {
    "X-Tenant-Id": TENANT_ID,
    "X-User-Id": USER_ID,
    "Content-Type": "application/json"
}


def print_step(step_num, message):
    """Print a formatted step message."""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {message}")
    print('='*60)


def print_success(message):
    """Print a success message."""
    print(f"✓ SUCCESS: {message}")


def print_error(message):
    """Print an error message."""
    print(f"✗ ERROR: {message}")
    sys.exit(1)


def create_assessment():
    """Create a test assessment."""
    print_step(1, "Creating Test Assessment")
    
    assessment_data = {
        "title": "Test Assessment for Recommendation Feature",
        "description": "Testing if recommendations save correctly",
        "system_background": "Test system",
        "scope": "Testing",
        "tech_stack": ["Python", "FastAPI"],
        "overall_impact": "Medium"
    }
    
    response = requests.post(
        f"{API_BASE}/assessments/",
        json=assessment_data,
        headers=headers
    )
    
    if response.status_code != 201:
        print_error(f"Failed to create assessment: {response.text}")
    
    assessment = response.json()
    print_success(f"Assessment created with ID: {assessment['id']}")
    print(f"Assessment: {json.dumps(assessment, indent=2)}")
    return assessment['id']


def create_threat(assessment_id):
    """Create a test threat."""
    print_step(2, "Creating Test Threat")
    
    threat_data = {
        "title": "Test Threat for Recommendation",
        "description": "This is a test threat to verify recommendation saving",
        "likelihood": "Medium",
        "impact": "High",
        "cve_ids": [],
        "status": "identified"
    }
    
    response = requests.post(
        f"{API_BASE}/threats/?assessment_id={assessment_id}",
        json=threat_data,
        headers=headers
    )
    
    if response.status_code != 201:
        print_error(f"Failed to create threat: {response.text}")
    
    threat = response.json()
    print_success(f"Threat created with ID: {threat['id']}")
    print(f"Threat: {json.dumps(threat, indent=2)}")
    return threat['id']


def update_threat_with_recommendation(threat_id, recommendation_text):
    """Update the threat with a recommendation."""
    print_step(3, "Updating Threat with Recommendation")
    
    update_data = {
        "title": "Test Threat for Recommendation (Updated)",
        "description": "Updated description",
        "recommendation": recommendation_text,
        "likelihood": "Medium",
        "impact": "High"
    }
    
    print(f"Sending update payload: {json.dumps(update_data, indent=2)}")
    
    response = requests.patch(
        f"{API_BASE}/threats/{threat_id}",
        json=update_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print_error(f"Failed to update threat: {response.text}")
    
    updated_threat = response.json()
    print_success(f"Threat updated successfully")
    print(f"Updated Threat: {json.dumps(updated_threat, indent=2)}")
    return updated_threat


def verify_recommendation(threat_id, expected_recommendation):
    """Fetch the threat and verify the recommendation was saved."""
    print_step(4, "Verifying Recommendation was Saved")
    
    response = requests.get(
        f"{API_BASE}/threats/{threat_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print_error(f"Failed to fetch threat: {response.text}")
    
    threat = response.json()
    print(f"Fetched Threat: {json.dumps(threat, indent=2)}")
    
    # Check if recommendation field exists
    if 'recommendation' not in threat:
        print_error("Recommendation field not found in response!")
    
    # Check if recommendation matches
    actual_recommendation = threat.get('recommendation')
    if actual_recommendation == expected_recommendation:
        print_success(f"Recommendation verified! Value: '{actual_recommendation}'")
        return True
    else:
        print_error(f"Recommendation mismatch!\nExpected: '{expected_recommendation}'\nActual: '{actual_recommendation}'")
        return False


def cleanup(assessment_id, threat_id):
    """Optional: Clean up test data."""
    print_step(5, "Cleanup (Optional)")
    
    # Delete threat
    response = requests.delete(
        f"{API_BASE}/threats/{threat_id}",
        headers=headers
    )
    if response.status_code == 204:
        print_success("Test threat deleted")
    else:
        print(f"Warning: Could not delete threat: {response.text}")
    
    # Delete assessment
    response = requests.delete(
        f"{API_BASE}/assessments/{assessment_id}",
        headers=headers
    )
    if response.status_code == 204:
        print_success("Test assessment deleted")
    else:
        print(f"Warning: Could not delete assessment: {response.text}")


def main():
    """Run the test."""
    print("\n" + "="*60)
    print("RECOMMENDATION FIELD SAVE FEATURE TEST")
    print("="*60)
    
    recommendation_text = "Implement multi-factor authentication and regular security audits to mitigate this threat."
    
    try:
        # Step 1: Create assessment
        assessment_id = create_assessment()
        
        # Step 2: Create threat
        threat_id = create_threat(assessment_id)
        
        # Step 3: Update threat with recommendation
        updated_threat = update_threat_with_recommendation(threat_id, recommendation_text)
        
        # Step 4: Verify recommendation was saved
        verify_recommendation(threat_id, recommendation_text)
        
        # Final summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print_success("All tests passed!")
        print(f"\nTest Assessment ID: {assessment_id}")
        print(f"Test Threat ID: {threat_id}")
        print(f"Recommendation: '{recommendation_text}'")
        
        # Ask if user wants to clean up
        print("\n" + "-"*60)
        cleanup_choice = input("Do you want to delete the test data? (y/n): ").strip().lower()
        if cleanup_choice == 'y':
            cleanup(assessment_id, threat_id)
        else:
            print("Test data preserved for manual inspection.")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    print("\nNOTE: Make sure to update TENANT_ID and USER_ID with your actual IDs!")
    print("You can find these by checking your database or existing API responses.\n")
    
    # Optionally, allow command line arguments
    if len(sys.argv) > 1:
        TENANT_ID = sys.argv[1]
    if len(sys.argv) > 2:
        USER_ID = sys.argv[2]
    if len(sys.argv) > 3:
        ASSESSMENT_ID = sys.argv[3]
    
    main()
