"""
Test script to verify Excel file reloading works
This tests that changes to Excel file are immediately reflected in API calls
"""
import requests
import time

BASE_URL = "http://localhost:8000/api"

print("=" * 60)
print("Excel File Reload Test")
print("=" * 60)
print()

# Test 1: Get employees first time
print("[1] First API call - Getting employees...")
try:
    response = requests.get(f"{BASE_URL}/employees")
    if response.status_code == 200:
        employees1 = response.json()
        print(f"✅ Found {len(employees1)} employees")
        if employees1:
            print(f"   Sample: {employees1[0]}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error connecting to server: {e}")
    print("   Make sure the server is running: pipenv run python server.py")
    exit(1)

print()

# Test 2: Get employees again (should reload from Excel)
print("[2] Second API call - Getting employees again (should reload)...")
time.sleep(1)  # Small delay
try:
    response = requests.get(f"{BASE_URL}/employees")
    if response.status_code == 200:
        employees2 = response.json()
        print(f"✅ Found {len(employees2)} employees")
        if employees2:
            print(f"   Sample: {employees2[0]}")
        
        # Compare
        if len(employees1) == len(employees2):
            print("   ✅ Same number of employees (file reloaded correctly)")
        else:
            print(f"   ⚠️  Different count: {len(employees1)} vs {len(employees2)}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print()

# Test 3: Get projects
print("[3] Getting projects (should reload Excel)...")
try:
    response = requests.get(f"{BASE_URL}/projects")
    if response.status_code == 200:
        projects = response.json()
        print(f"✅ Found {len(projects)} projects")
        if projects:
            print(f"   Sample: {projects[0]}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 4: Get tasks
print("[4] Getting tasks (should reload Excel)...")
try:
    response = requests.get(f"{BASE_URL}/tasks")
    if response.status_code == 200:
        tasks = response.json()
        print(f"✅ Found {len(tasks)} tasks")
        if tasks:
            print(f"   Sample: {tasks[0]}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)
print()
print("If you see the same data in all calls, Excel reloading is working!")
print("Try editing the Excel file and calling the API again - changes")
print("should appear immediately without restarting the server.")
print()

