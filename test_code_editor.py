"""
Comprehensive test suite for CodeEditorAgent
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.code_editor import CodeEditorAgent
from agents.base import Task


class CodeEditorTestSuite:
    """Test suite for validating CodeEditorAgent functionality."""
    
    def __init__(self):
        self.agent = CodeEditorAgent()
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        print("🧪 Starting CodeEditorAgent Test Suite")
        print("=" * 50)
        
        # Initialize agent
        self.agent.lazy_load_model()
        
        # Test scenarios
        await self.test_simple_function_modification()
        await self.test_variable_renaming()
        await self.test_add_error_handling()
        await self.test_syntax_validation()
        await self.test_language_detection()
        await self.test_invalid_inputs()
        
        # Summary
        self.print_summary()
    
    async def test_simple_function_modification(self):
        """Test modifying a simple function."""
        print("\n📝 Test 1: Simple Function Modification")
        
        original_code = """def calculate_area(length, width):
    return length * width

def main():
    area = calculate_area(10, 5)
    print(area)"""
        
        instructions = "Add type hints to the calculate_area function parameters and return value"
        
        task = Task(
            prompt=instructions,
            context={
                "code_to_edit": original_code,
                "language": "python"
            }
        )
        
        result = await self.agent.execute(task)
        
        success = (
            result.status == "success" and
            "length: " in result.output and
            "width: " in result.output and
            "-> " in result.output
        )
        
        self.test_results.append({
            "name": "Simple Function Modification",
            "success": success,
            "details": f"Status: {result.status}, Type hints added: {'Yes' if success else 'No'}"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
        if result.status == "success":
            print(f"   Preview: {result.output[:100]}...")
    
    async def test_variable_renaming(self):
        """Test renaming variables in code."""
        print("\n📝 Test 2: Variable Renaming")
        
        original_code = """def process_data(data):
    result = []
    for item in data:
        processed_item = item * 2
        result.append(processed_item)
    return result"""
        
        instructions = "Rename the variable 'result' to 'output_list' throughout the function"
        
        task = Task(
            prompt=instructions,
            context={
                "code_to_edit": original_code,
                "language": "python"
            }
        )
        
        result = await self.agent.execute(task)
        
        success = (
            result.status == "success" and
            "output_list" in result.output and
            result.output.count("result") == 0  # No old variable name should remain
        )
        
        self.test_results.append({
            "name": "Variable Renaming",
            "success": success,
            "details": f"Status: {result.status}, Variable renamed: {'Yes' if success else 'No'}"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
    
    async def test_add_error_handling(self):
        """Test adding error handling to code."""
        print("\n📝 Test 3: Add Error Handling")
        
        original_code = """def divide_numbers(a, b):
    return a / b

def main():
    result = divide_numbers(10, 0)
    print(result)"""
        
        instructions = "Add try-except error handling to the divide_numbers function to handle division by zero"
        
        task = Task(
            prompt=instructions,
            context={
                "code_to_edit": original_code,
                "language": "python"
            }
        )
        
        result = await self.agent.execute(task)
        
        success = (
            result.status == "success" and
            "try:" in result.output and
            "except" in result.output and
            "ZeroDivisionError" in result.output or "Exception" in result.output
        )
        
        self.test_results.append({
            "name": "Add Error Handling",
            "success": success,
            "details": f"Status: {result.status}, Error handling added: {'Yes' if success else 'No'}"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
    
    async def test_syntax_validation(self):
        """Test that the agent validates syntax of generated code."""
        print("\n📝 Test 4: Syntax Validation")
        
        # This test checks if the agent can handle its own output validation
        original_code = """def test_function():
    x = 1
    y = 2
    return x + y"""
        
        instructions = "Add a print statement at the end of the function to display the result"
        
        task = Task(
            prompt=instructions,
            context={
                "code_to_edit": original_code,
                "language": "python"
            }
        )
        
        result = await self.agent.execute(task)
        
        # If result is successful, the syntax validation passed
        success = result.status == "success"
        
        # Additional check: try to compile the output
        if success:
            try:
                compile(result.output, '<string>', 'exec')
                syntax_valid = True
            except SyntaxError:
                syntax_valid = False
                success = False
        else:
            syntax_valid = False
        
        self.test_results.append({
            "name": "Syntax Validation",
            "success": success,
            "details": f"Status: {result.status}, Syntax valid: {'Yes' if syntax_valid else 'No'}"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
    
    async def test_language_detection(self):
        """Test language detection capability."""
        print("\n📝 Test 5: Language Detection")
        
        # Test with JavaScript code
        js_code = """function calculateSum(a, b) {
    return a + b;
}

const result = calculateSum(5, 3);
console.log(result);"""
        
        # Test the internal language detection (access via orchestrator)
        from agents.orchestrator import ProjectManager
        pm = ProjectManager()
        detected_language = pm._detect_language(js_code)
        
        success = detected_language == "javascript"
        
        self.test_results.append({
            "name": "Language Detection",
            "success": success,
            "details": f"Detected: {detected_language}, Expected: javascript"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
    
    async def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        print("\n📝 Test 6: Invalid Input Handling")
        
        # Test with missing code
        task = Task(
            prompt="Add comments to this code",
            context={}  # Missing code_to_edit
        )
        
        result = await self.agent.execute(task)
        
        success = result.status == "failure" and "code_to_edit" in result.error_message
        
        self.test_results.append({
            "name": "Invalid Input Handling",
            "success": success,
            "details": f"Status: {result.status}, Proper error handling: {'Yes' if success else 'No'}"
        })
        
        print(f"   {'✅' if success else '❌'} {self.test_results[-1]['details']}")
    
    def print_summary(self):
        """Print test results summary."""
        print("\n📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["success"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test in self.test_results:
            status_icon = "✅" if test["success"] else "❌"
            print(f"  {status_icon} {test['name']}: {test['details']}")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! CodeEditorAgent is working correctly.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review implementation.")


async def test_integration_workflow():
    """Test integration with ProjectManager workflow."""
    print("\n🔗 INTEGRATION WORKFLOW TEST")
    print("=" * 50)
    
    # Test the orchestrator's ability to handle code editing requests
    from agents.orchestrator import ProjectManager
    
    pm = ProjectManager()
    
    # Test prompt that should trigger code editing workflow
    test_prompt = "Fix the bug in the calculate_total function by adding null checks"
    
    # Check if the orchestrator can create a proper plan
    plan = await pm._decompose_prompt(test_prompt)
    
    print(f"Generated plan steps: {len(plan)}")
    for i, step in enumerate(plan, 1):
        print(f"  Step {i}: {step['agent_role']} - {step['prompt'][:50]}...")
    
    # Check if code_editor is in the plan
    has_code_editor = any(step['agent_role'] == 'code_editor' for step in plan)
    
    print(f"\nCode editor in workflow: {'✅ Yes' if has_code_editor else '❌ No'}")
    
    await pm.cleanup()


async def main():
    """Run the complete test suite."""
    # Run individual agent tests
    test_suite = CodeEditorTestSuite()
    await test_suite.run_all_tests()
    
    # Run integration tests
    await test_integration_workflow()


if __name__ == "__main__":
    asyncio.run(main())