#!/usr/bin/env python3
"""
Test script for the list travels endpoint.
"""

import requests
import json
from datetime import datetime

def test_list_travels():
    """Test the list travels endpoint"""
    base_url = "http://localhost:5555"
    
    print("=== Testing List Travels Endpoint ===")
    
    # Test 1: Basic listing without filters
    print("\n1. Testing basic listing...")
    try:
        response = requests.get(f"{base_url}/api/travels/")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Total travels: {data['pagination']['total']}")
            print(f"Returned travels: {len(data['data'])}")
            print(f"Pagination: page {data['pagination']['page']} of {data['pagination']['pages']}")
            
            # Show first travel if available
            if data['data']:
                first_travel = data['data'][0]
                print(f"First travel: {first_travel['title']} to {first_travel['destination']}")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on port 5555.")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: With pagination
    print("\n2. Testing pagination...")
    try:
        response = requests.get(f"{base_url}/api/travels/?limit=2&offset=0")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Limit: {data['pagination']['limit']}")
            print(f"Offset: {data['pagination']['offset'] if 'offset' in data['pagination'] else 'N/A'}")
            print(f"Returned travels: {len(data['data'])}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: With title filter
    print("\n3. Testing title filter...")
    try:
        response = requests.get(f"{base_url}/api/travels/?title=Paris")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Filtered by 'Paris': {len(data['data'])} travels found")
            for travel in data['data']:
                print(f"  - {travel['title']} to {travel['destination']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: With destination filter
    print("\n4. Testing destination filter...")
    try:
        response = requests.get(f"{base_url}/api/travels/?destination=Japan")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Filtered by 'Japan': {len(data['data'])} travels found")
            for travel in data['data']:
                print(f"  - {travel['title']} to {travel['destination']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: With date range filter
    print("\n5. Testing date range filter...")
    try:
        response = requests.get(f"{base_url}/api/travels/?start_date_from=2024-06-01&start_date_to=2024-06-30")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Filtered by June 2024: {len(data['data'])} travels found")
            for travel in data['data']:
                print(f"  - {travel['title']} ({travel['start_date']} to {travel['end_date']})")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_list_travels()
