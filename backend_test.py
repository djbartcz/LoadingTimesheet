#!/usr/bin/env python3
"""
Backend API Testing for Czech Loading/Unloading Time Tracking Application
Tests Google Sheets integration and timer functionality
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional

class LoadTrackAPITester:
    def __init__(self, base_url="https://loadtrack-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.active_timer_id = None

    def log_test(self, name: str, success: bool, details: str = "", response_data: Dict = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict = None, headers: Dict = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            details = f"Status: {response.status_code} (expected {expected_status})"
            if not success:
                details += f", Response: {response.text[:200]}"

            self.log_test(name, success, details, response_data)
            return success, response_data

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)

    def test_get_employees(self):
        """Test getting employees from Google Sheets"""
        success, data = self.run_test("Get Employees", "GET", "employees", 200)
        if success and isinstance(data, list):
            print(f"    Found {len(data)} employees")
            for emp in data[:3]:  # Show first 3
                print(f"      - {emp.get('name', 'Unknown')} (ID: {emp.get('id', 'N/A')})")
        return success, data

    def test_get_projects(self):
        """Test getting projects from Google Sheets"""
        success, data = self.run_test("Get Projects", "GET", "projects", 200)
        if success and isinstance(data, list):
            print(f"    Found {len(data)} projects")
            for proj in data[:3]:  # Show first 3
                print(f"      - {proj.get('name', 'Unknown')} (ID: {proj.get('id', 'N/A')})")
        return success, data

    def test_get_tasks(self):
        """Test getting tasks from Google Sheets"""
        success, data = self.run_test("Get Tasks", "GET", "tasks", 200)
        if success and isinstance(data, list):
            print(f"    Found {len(data)} tasks")
            for task in data:
                print(f"      - {task.get('name', 'Unknown')}")
        return success, data

    def test_start_timer(self, employee_data: Dict, project_data: Dict, task_name: str):
        """Test starting a timer"""
        if not employee_data or not project_data:
            self.log_test("Start Timer", False, "Missing employee or project data")
            return False, {}

        timer_data = {
            "employee_id": employee_data.get('id', 'test_emp_1'),
            "employee_name": employee_data.get('name', 'Test Employee'),
            "project_id": project_data.get('id', 'test_proj_1'),
            "project_name": project_data.get('name', 'Test Project'),
            "task": task_name
        }

        success, data = self.run_test("Start Timer", "POST", "timer/start", 200, timer_data)
        if success and data.get('id'):
            self.active_timer_id = data['id']
            print(f"    Timer started with ID: {self.active_timer_id}")
        return success, data

    def test_get_active_timer(self, employee_id: str):
        """Test getting active timer for employee"""
        success, data = self.run_test("Get Active Timer", "GET", f"timer/active/{employee_id}", 200)
        if success and data:
            print(f"    Active timer found for employee {employee_id}")
            print(f"      Project: {data.get('project_name', 'Unknown')}")
            print(f"      Task: {data.get('task', 'Unknown')}")
        return success, data

    def test_stop_timer(self, timer_id: str, duration_seconds: int = 300):
        """Test stopping a timer"""
        if not timer_id:
            self.log_test("Stop Timer", False, "No timer ID provided")
            return False, {}

        stop_data = {
            "record_id": timer_id,
            "end_time": datetime.now().isoformat() + "Z",
            "duration_seconds": duration_seconds
        }

        success, data = self.run_test("Stop Timer", "POST", "timer/stop", 200, stop_data)
        if success:
            print(f"    Timer stopped and saved to Google Sheets")
        return success, data

    def run_full_test_suite(self):
        """Run complete test suite"""
        print("🚀 Starting LoadTrack API Test Suite")
        print("=" * 50)

        # Test basic connectivity
        print("\n📡 Testing API Connectivity...")
        self.test_api_root()

        # Test data retrieval endpoints
        print("\n📊 Testing Data Retrieval...")
        emp_success, employees = self.test_get_employees()
        proj_success, projects = self.test_get_projects()
        task_success, tasks = self.test_get_tasks()

        # Test timer functionality if we have data
        print("\n⏱️  Testing Timer Functionality...")
        
        if emp_success and employees and proj_success and projects and task_success and tasks:
            # Use first available employee, project, and task
            test_employee = employees[0] if employees else None
            test_project = projects[0] if projects else None
            test_task = tasks[0]['name'] if tasks else "NAKLÁDKA"

            if test_employee and test_project:
                # Start timer
                timer_success, timer_data = self.test_start_timer(test_employee, test_project, test_task)
                
                if timer_success and self.active_timer_id:
                    # Check active timer
                    self.test_get_active_timer(test_employee['id'])
                    
                    # Stop timer after a short duration
                    import time
                    time.sleep(2)  # Wait 2 seconds
                    self.test_stop_timer(self.active_timer_id, 2)
                else:
                    print("    ⚠️  Could not test timer stop - timer start failed")
            else:
                print("    ⚠️  Could not test timer functionality - missing employee or project data")
        else:
            print("    ⚠️  Could not test timer functionality - data retrieval failed")

        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed. Check the details above.")
            return 1

    def get_failed_tests(self) -> List[Dict]:
        """Get list of failed tests"""
        return [test for test in self.test_results if not test['success']]

    def get_test_summary(self) -> Dict:
        """Get test summary for reporting"""
        failed_tests = self.get_failed_tests()
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": len(failed_tests),
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "failed_test_details": failed_tests
        }

def main():
    """Main test execution"""
    tester = LoadTrackAPITester()
    
    try:
        exit_code = tester.run_full_test_suite()
        
        # Save detailed results
        summary = tester.get_test_summary()
        print(f"\n📋 Test Summary:")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())