#!/usr/bin/env python3
"""
CodeGuard AI - Demo Testing Script

This script demonstrates and tests the complete CodeGuard AI system functionality,
including all analysis features and the LLM integration.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.tree import Tree

# Initialize Rich console for beautiful output
console = Console()

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
TEST_TIMEOUT = 30

# Sample code snippets for testing
TEST_CODES = {
    "python_vulnerable": {
        "language": "python",
        "code": '''
import sqlite3
import hashlib

def login_user(username, password):
    # Vulnerable SQL injection
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result is not None

def hash_password(password):
    # Weak hashing algorithm
    return hashlib.md5(password.encode()).hexdigest()

class UserManager:
    def __init__(self):
        self.users = {}
        self.admin_key = "admin123"  # Hardcoded secret
    
    def create_user(self, username, password):
        # No input validation
        self.users[username] = hash_password(password)
        return True
''',
        "description": "Python code with SQL injection, weak crypto, and hardcoded secrets"
    },
    
    "javascript_performance": {
        "language": "javascript",
        "code": '''
// Performance issues and potential AI-generated patterns
function processLargeArray(data) {
    // Inefficient nested loops
    let result = [];
    for (let i = 0; i < data.length; i++) {
        for (let j = 0; j < data.length; j++) {
            for (let k = 0; k < data.length; k++) {
                if (data[i] + data[j] + data[k] === 0) {
                    result.push([data[i], data[j], data[k]]);
                }
            }
        }
    }
    return result;
}

// Potential AI-generated code patterns
function calculateSum(numbers) {
    // This function calculates the sum of an array of numbers
    let sum = 0; // Initialize sum to zero
    
    // Iterate through each number in the array
    for (let i = 0; i < numbers.length; i++) {
        // Add the current number to the sum
        sum += numbers[i];
    }
    
    // Return the calculated sum
    return sum;
}

// Memory leak potential
let globalCache = {};
function cacheData(key, value) {
    globalCache[key] = value; // Never cleaned up
}
''',
        "description": "JavaScript with performance issues and AI-generated patterns"
    },
    
    "java_quality": {
        "language": "java",
        "code": '''
public class DataProcessor {
    // Poor code quality examples
    public void processData(String data) {
        if (data != null) {
            if (data.length() > 0) {
                if (!data.isEmpty()) {
                    if (data.trim().length() > 0) {
                        // Deeply nested conditions
                        String[] parts = data.split(",");
                        for (int i = 0; i < parts.length; i++) {
                            if (parts[i] != null) {
                                if (parts[i].length() > 0) {
                                    // Process part
                                    System.out.println(parts[i]);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Duplicate code
    public void processUserData(String userData) {
        if (userData != null) {
            if (userData.length() > 0) {
                if (!userData.isEmpty()) {
                    if (userData.trim().length() > 0) {
                        String[] parts = userData.split(",");
                        for (int i = 0; i < parts.length; i++) {
                            if (parts[i] != null) {
                                if (parts[i].length() > 0) {
                                    System.out.println("User: " + parts[i]);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
''',
        "description": "Java code with quality issues and code duplication"
    }
}

class CodeGuardDemo:
    """Main demo class for testing CodeGuard AI functionality."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TEST_TIMEOUT)
        self.results = {}
        self.auth_token = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_services(self) -> bool:
        """Check if backend and frontend services are running."""
        console.print("\n[bold blue]🔍 Checking Services...[/bold blue]")
        
        # Check backend
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                console.print("✅ Backend service is running")
                backend_ok = True
            else:
                console.print(f"❌ Backend service error: {response.status_code}")
                backend_ok = False
        except Exception as e:
            console.print(f"❌ Backend service not accessible: {e}")
            backend_ok = False
        
        # Check frontend (optional)
        try:
            frontend_response = await self.client.get(FRONTEND_URL)
            if frontend_response.status_code == 200:
                console.print("✅ Frontend service is running")
            else:
                console.print("⚠️  Frontend service not accessible (optional)")
        except Exception:
            console.print("⚠️  Frontend service not accessible (optional)")
        
        return backend_ok
    
    async def test_basic_analysis(self) -> Dict[str, Any]:
        """Test basic code analysis functionality."""
        console.print("\n[bold green]🔬 Testing Basic Analysis...[/bold green]")
        
        results = {}
        
        for test_name, test_data in TEST_CODES.items():
            console.print(f"\n[cyan]Testing {test_name}...[/cyan]")
            
            # Prepare analysis request
            analysis_request = {
                "code": test_data["code"],
                "language": test_data["language"],
                "analysis_types": ["ai_detection", "security", "performance", "quality"]
            }
            
            try:
                response = await self.client.post(
                    f"{BASE_URL}/api/v1/analyze",
                    json=analysis_request
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results[test_name] = result
                    
                    # Display summary
                    self._display_analysis_summary(test_name, result)
                    
                else:
                    console.print(f"❌ Analysis failed: {response.status_code}")
                    results[test_name] = {"error": f"HTTP {response.status_code}"}
            
            except Exception as e:
                console.print(f"❌ Analysis error: {e}")
                results[test_name] = {"error": str(e)}
        
        return results
    
    async def test_llm_integration(self) -> Dict[str, Any]:
        """Test LLM integration features."""
        console.print("\n[bold magenta]🤖 Testing LLM Integration...[/bold magenta]")
        
        # Check if LLM service is available
        try:
            health_response = await self.client.get(f"{BASE_URL}/llm/health")
            if health_response.status_code != 200:
                console.print("⚠️  LLM service not available - skipping LLM tests")
                return {"skipped": "LLM service not available"}
        except Exception as e:
            console.print(f"⚠️  LLM service not accessible: {e} - skipping LLM tests")
            return {"skipped": f"LLM service error: {e}"}
        
        results = {}
        test_code = TEST_CODES["python_vulnerable"]
        
        # Test code analysis with LLM
        console.print("[cyan]Testing LLM code analysis...[/cyan]")
        try:
            llm_request = {
                "code": test_code["code"],
                "language": test_code["language"],
                "existing_issues": []
            }
            
            response = await self.client.post(
                f"{BASE_URL}/llm/analyze-code",
                json=llm_request
            )
            
            if response.status_code == 200:
                result = response.json()
                results["code_analysis"] = result
                console.print(f"✅ LLM Analysis - Confidence: {result.get('confidence', 0):.2f}")
            else:
                console.print(f"❌ LLM Analysis failed: {response.status_code}")
        
        except Exception as e:
            console.print(f"❌ LLM Analysis error: {e}")
        
        # Test AI detection
        console.print("[cyan]Testing AI code detection...[/cyan]")
        try:
            ai_request = {
                "code": TEST_CODES["javascript_performance"]["code"],
                "language": "javascript"
            }
            
            response = await self.client.post(
                f"{BASE_URL}/llm/detect-ai-code",
                json=ai_request
            )
            
            if response.status_code == 200:
                result = response.json()
                results["ai_detection"] = result
                console.print(f"✅ AI Detection - Confidence: {result.get('confidence', 0):.2f}")
            else:
                console.print(f"❌ AI Detection failed: {response.status_code}")
        
        except Exception as e:
            console.print(f"❌ AI Detection error: {e}")
        
        return results
    
    async def test_api_endpoints(self) -> Dict[str, Any]:
        """Test various API endpoints."""
        console.print("\n[bold yellow]🔗 Testing API Endpoints...[/bold yellow]")
        
        endpoints_to_test = [
            ("/health", "GET", "Health Check"),
            ("/api/v1/supported-languages", "GET", "Supported Languages"),
            ("/api/v1/statistics", "GET", "Statistics"),
            ("/llm/capabilities", "GET", "LLM Capabilities")
        ]
        
        results = {}
        
        for endpoint, method, description in endpoints_to_test:
            console.print(f"[cyan]Testing {description}...[/cyan]")
            
            try:
                if method == "GET":
                    response = await self.client.get(f"{BASE_URL}{endpoint}")
                else:
                    response = await self.client.post(f"{BASE_URL}{endpoint}")
                
                if response.status_code == 200:
                    console.print(f"✅ {description} - OK")
                    results[endpoint] = {"status": "success", "data": response.json()}
                else:
                    console.print(f"❌ {description} - HTTP {response.status_code}")
                    results[endpoint] = {"status": "error", "code": response.status_code}
            
            except Exception as e:
                console.print(f"❌ {description} - Error: {e}")
                results[endpoint] = {"status": "error", "message": str(e)}
        
        return results
    
    def _display_analysis_summary(self, test_name: str, result: Dict[str, Any]):
        """Display a summary of analysis results."""
        table = Table(title=f"Analysis Results: {test_name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Security issues
        security_issues = result.get("security_analysis", {}).get("issues", [])
        table.add_row("Security Issues", str(len(security_issues)))
        
        # Performance issues
        performance_issues = result.get("performance_analysis", {}).get("issues", [])
        table.add_row("Performance Issues", str(len(performance_issues)))
        
        # Quality score
        quality_score = result.get("quality_assessment", {}).get("overall_score", 0)
        table.add_row("Quality Score", f"{quality_score:.1f}/100")
        
        # AI detection
        ai_confidence = result.get("ai_detection", {}).get("confidence", 0)
        table.add_row("AI Detection Confidence", f"{ai_confidence:.2f}")
        
        console.print(table)
    
    async def generate_demo_report(self, all_results: Dict[str, Any]):
        """Generate a comprehensive demo report."""
        console.print("\n[bold blue]📊 Generating Demo Report...[/bold blue]")
        
        # Create report structure
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0
            },
            "results": all_results
        }
        
        # Calculate summary statistics
        for category, results in all_results.items():
            if isinstance(results, dict):
                for test_name, test_result in results.items():
                    report["summary"]["total_tests"] += 1
                    # Check for both non-null "error" values and "status": "error" patterns
                    has_error = test_result.get("error") is not None
                    has_error_status = test_result.get("status") == "error"
                    
                    if not has_error and not has_error_status:
                        report["summary"]["successful_tests"] += 1
                    else:
                        report["summary"]["failed_tests"] += 1
        
        # Save report to file
        report_path = Path("demo_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        console.print(f"✅ Demo report saved to: {report_path}")
        
        # Display summary
        summary_table = Table(title="Demo Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="green")
        
        summary_table.add_row("Total Tests", str(report["summary"]["total_tests"]))
        summary_table.add_row("Successful", str(report["summary"]["successful_tests"]))
        summary_table.add_row("Failed", str(report["summary"]["failed_tests"]))
        
        success_rate = (report["summary"]["successful_tests"] / 
                       max(report["summary"]["total_tests"], 1)) * 100
        summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        console.print(summary_table)
        
        return report


async def main():
    """Main demo function."""
    console.print(Panel.fit(
        "[bold blue]CodeGuard AI - Complete System Demo[/bold blue]\n"
        "This demo tests all major functionality including:\n"
        "• Multi-language code analysis\n"
        "• Security vulnerability detection\n"
        "• Performance analysis\n"
        "• Code quality assessment\n"
        "• AI-generated code detection\n"
        "• LLM integration features",
        title="🛡️  CodeGuard AI Demo"
    ))
    
    async with CodeGuardDemo() as demo:
        all_results = {}
        
        # Check if services are running
        if not await demo.check_services():
            console.print("\n❌ Backend service is not running. Please start the backend first.")
            console.print("Run: cd backend && python -m uvicorn app.main:app --reload")
            return
        
        # Run all tests
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Basic analysis tests
            task1 = progress.add_task("Running basic analysis tests...", total=None)
            all_results["basic_analysis"] = await demo.test_basic_analysis()
            progress.update(task1, completed=True)
            
            # LLM integration tests
            task2 = progress.add_task("Running LLM integration tests...", total=None)
            all_results["llm_integration"] = await demo.test_llm_integration()
            progress.update(task2, completed=True)
            
            # API endpoint tests
            task3 = progress.add_task("Running API endpoint tests...", total=None)
            all_results["api_endpoints"] = await demo.test_api_endpoints()
            progress.update(task3, completed=True)
        
        # Generate comprehensive report
        report = await demo.generate_demo_report(all_results)
        
        # Final recommendations
        console.print("\n[bold green]🎉 Demo Complete![/bold green]")
        console.print("\n[bold yellow]Next Steps:[/bold yellow]")
        console.print("1. Review the generated demo_report.json for detailed results")
        console.print("2. Check the web dashboard at http://localhost:3000")
        console.print("3. Explore the API documentation at http://localhost:8000/docs")
        console.print("4. Set up your OpenAI API key for full LLM functionality")
        
        if "skipped" in all_results.get("llm_integration", {}):
            console.print("\n[yellow]⚠️  LLM features were skipped. To enable:[/yellow]")
            console.print("   export OPENAI_API_KEY='your-api-key-here'")
            console.print("   export LLM_ENABLED=true")


if __name__ == "__main__":
    # Check if required packages are available
    try:
        import httpx
        import rich
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Install with: pip install httpx rich")
        sys.exit(1)
    
    # Run the demo
    asyncio.run(main())