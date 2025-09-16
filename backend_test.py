#!/usr/bin/env python3
"""
Backend API Tests for Zoomage NASA Image Explorer
Tests all core functionality including NASA API integration, AI analysis, and labeling system.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://zoomage-explore.preview.emergentagent.com/api"
TIMEOUT = 30

class ZoomageAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_results = []
        self.test_image_id = None
        self.test_label_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_health_check(self):
        """Test basic API health check"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Zoomage" in data["message"]:
                    self.log_test("Health Check", True, f"API responding correctly: {data['message']}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected response format: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_nasa_search(self):
        """Test NASA API integration with search functionality"""
        try:
            # Test with mars rover query
            search_data = {
                "query": "mars rover",
                "media_type": "image"
            }
            
            response = self.session.post(
                f"{self.base_url}/search", 
                json=search_data,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Store first image ID for later tests
                    self.test_image_id = data[0].get("id")
                    
                    # Verify image structure
                    first_image = data[0]
                    required_fields = ["id", "nasa_id", "title", "url"]
                    missing_fields = [field for field in required_fields if field not in first_image]
                    
                    if not missing_fields:
                        self.log_test("NASA Search", True, 
                                    f"Found {len(data)} images, first image: {first_image.get('title', 'No title')}")
                        return True
                    else:
                        self.log_test("NASA Search", False, 
                                    f"Missing required fields: {missing_fields}")
                        return False
                else:
                    self.log_test("NASA Search", False, "No images returned from search")
                    return False
            else:
                self.log_test("NASA Search", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("NASA Search", False, f"Error: {str(e)}")
            return False
    
    def test_ai_analysis(self):
        """Test AI analysis functionality"""
        try:
            # First, get an image to analyze
            if not self.test_image_id:
                # Try to get saved images
                response = self.session.get(f"{self.base_url}/images", timeout=TIMEOUT)
                if response.status_code == 200:
                    images = response.json()
                    if images:
                        test_image_url = images[0].get("url")
                    else:
                        self.log_test("AI Analysis", False, "No images available for analysis")
                        return False
                else:
                    self.log_test("AI Analysis", False, "Could not retrieve images for analysis")
                    return False
            else:
                # Get the test image details
                response = self.session.get(f"{self.base_url}/images/{self.test_image_id}", timeout=TIMEOUT)
                if response.status_code == 200:
                    image_data = response.json()
                    test_image_url = image_data.get("url")
                else:
                    self.log_test("AI Analysis", False, "Could not get test image details")
                    return False
            
            # Test AI analysis
            analysis_data = {
                "image_url": test_image_url,
                "analysis_type": "general"
            }
            
            response = self.session.post(
                f"{self.base_url}/analyze",
                json=analysis_data,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if "analysis" in data and data["analysis"]:
                    analysis_text = data["analysis"]
                    if len(analysis_text) > 50:  # Reasonable analysis length
                        self.log_test("AI Analysis", True, 
                                    f"AI analysis completed: {analysis_text[:100]}...")
                        return True
                    else:
                        self.log_test("AI Analysis", False, 
                                    f"Analysis too short: {analysis_text}")
                        return False
                else:
                    self.log_test("AI Analysis", False, "No analysis returned")
                    return False
            else:
                self.log_test("AI Analysis", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("AI Analysis", False, f"Error: {str(e)}")
            return False
    
    def test_image_labeling_crud(self):
        """Test image labeling CRUD operations"""
        try:
            if not self.test_image_id:
                self.log_test("Image Labeling CRUD", False, "No test image ID available")
                return False
            
            # Test adding a label
            label_data = {
                "x": 0.5,
                "y": 0.3,
                "width": 0.1,
                "height": 0.1,
                "label": "Crater",
                "description": "Large impact crater visible in the image",
                "category": "geological"
            }
            
            response = self.session.post(
                f"{self.base_url}/images/{self.test_image_id}/labels",
                json=label_data,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                label_response = response.json()
                self.test_label_id = label_response.get("id")
                
                # Test retrieving labels
                response = self.session.get(
                    f"{self.base_url}/images/{self.test_image_id}/labels",
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    labels = response.json()
                    if isinstance(labels, list) and len(labels) > 0:
                        found_label = any(label.get("label") == "Crater" for label in labels)
                        if found_label:
                            # Test deleting the label
                            if self.test_label_id:
                                delete_response = self.session.delete(
                                    f"{self.base_url}/images/{self.test_image_id}/labels/{self.test_label_id}",
                                    timeout=TIMEOUT
                                )
                                
                                if delete_response.status_code == 200:
                                    self.log_test("Image Labeling CRUD", True, 
                                                "Successfully added, retrieved, and deleted label")
                                    return True
                                else:
                                    self.log_test("Image Labeling CRUD", False, 
                                                f"Failed to delete label: {delete_response.status_code}")
                                    return False
                            else:
                                self.log_test("Image Labeling CRUD", True, 
                                            "Successfully added and retrieved label (no ID for deletion)")
                                return True
                        else:
                            self.log_test("Image Labeling CRUD", False, 
                                        "Added label not found in retrieval")
                            return False
                    else:
                        self.log_test("Image Labeling CRUD", False, 
                                    "No labels returned after adding")
                        return False
                else:
                    self.log_test("Image Labeling CRUD", False, 
                                f"Failed to retrieve labels: {response.status_code}")
                    return False
            else:
                self.log_test("Image Labeling CRUD", False, 
                            f"Failed to add label: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Image Labeling CRUD", False, f"Error: {str(e)}")
            return False
    
    def test_pattern_discovery(self):
        """Test pattern discovery functionality"""
        try:
            response = self.session.get(f"{self.base_url}/discover", timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if "patterns" in data:
                    patterns = data["patterns"]
                    if isinstance(patterns, str) and len(patterns) > 20:
                        self.log_test("Pattern Discovery", True, 
                                    f"Pattern analysis completed: {patterns[:100]}...")
                        return True
                    else:
                        self.log_test("Pattern Discovery", True, 
                                    f"Pattern discovery returned: {patterns}")
                        return True
                else:
                    self.log_test("Pattern Discovery", False, "No patterns field in response")
                    return False
            else:
                self.log_test("Pattern Discovery", False, 
                            f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Pattern Discovery", False, f"Error: {str(e)}")
            return False
    
    def test_additional_search_queries(self):
        """Test additional search queries as specified"""
        queries = ["earth", "hubble", "mars"]
        all_passed = True
        
        for query in queries:
            try:
                search_data = {
                    "query": query,
                    "media_type": "image"
                }
                
                response = self.session.post(
                    f"{self.base_url}/search", 
                    json=search_data,
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        self.log_test(f"Search Query '{query}'", True, 
                                    f"Found {len(data)} images")
                    else:
                        self.log_test(f"Search Query '{query}'", False, "No images returned")
                        all_passed = False
                else:
                    self.log_test(f"Search Query '{query}'", False, 
                                f"HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Search Query '{query}'", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_ai_analysis_types(self):
        """Test different AI analysis types"""
        if not self.test_image_id:
            self.log_test("AI Analysis Types", False, "No test image available")
            return False
            
        # Get test image URL
        try:
            response = self.session.get(f"{self.base_url}/images/{self.test_image_id}", timeout=TIMEOUT)
            if response.status_code != 200:
                self.log_test("AI Analysis Types", False, "Could not get test image")
                return False
            
            image_data = response.json()
            test_image_url = image_data.get("url")
            
            analysis_types = ["features", "patterns"]
            all_passed = True
            
            for analysis_type in analysis_types:
                analysis_data = {
                    "image_url": test_image_url,
                    "analysis_type": analysis_type
                }
                
                response = self.session.post(
                    f"{self.base_url}/analyze",
                    json=analysis_data,
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "analysis" in data and data["analysis"]:
                        self.log_test(f"AI Analysis '{analysis_type}'", True, 
                                    f"Analysis completed: {data['analysis'][:50]}...")
                    else:
                        self.log_test(f"AI Analysis '{analysis_type}'", False, "No analysis returned")
                        all_passed = False
                else:
                    self.log_test(f"AI Analysis '{analysis_type}'", False, 
                                f"HTTP {response.status_code}")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_test("AI Analysis Types", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Zoomage NASA Image Explorer Backend Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Core functionality tests
        tests = [
            ("Health Check", self.test_health_check),
            ("NASA Search", self.test_nasa_search),
            ("AI Analysis", self.test_ai_analysis),
            ("Image Labeling CRUD", self.test_image_labeling_crud),
            ("Pattern Discovery", self.test_pattern_discovery),
            ("Additional Search Queries", self.test_additional_search_queries),
            ("AI Analysis Types", self.test_ai_analysis_types)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Unexpected error: {str(e)}")
            
            # Small delay between tests
            time.sleep(1)
        
        print("=" * 60)
        print(f"🏁 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All backend tests PASSED!")
            return True
        else:
            print(f"⚠️  {total - passed} tests FAILED")
            print("\nFailed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
            return False

def main():
    """Main test execution"""
    tester = ZoomageAPITester()
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()