"""
Error Analysis and Classification System

This module provides sophisticated error recognition, classification, and analysis
capabilities for the Enhanced Tool Executor Agent. It handles various types of
terminal command errors and provides structured analysis for recovery workflows.

Key Features:
- Multi-layered error classification (syntax, runtime, system, code)
- Pattern-based and LLM-powered error analysis
- Structured error context extraction
- Integration with recovery workflow routing
- Comprehensive audit logging

Author: Claude Code Assistant
Date: 2025-01-26
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors that can occur during command execution."""
    CODE_ERROR = "code_error"              # Python tracebacks, compilation errors
    COMMAND_SYNTAX = "command_syntax"      # Invalid command syntax, missing args
    SYSTEM_ERROR = "system_error"          # File not found, permissions, services
    NETWORK_ERROR = "network_error"        # Connection timeouts, DNS failures
    DEPENDENCY_ERROR = "dependency_error"  # Missing packages, version conflicts
    CONFIGURATION_ERROR = "config_error"  # Missing config files, invalid settings
    UNKNOWN_ERROR = "unknown_error"        # Unclassified errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"           # Warnings, minor issues
    MEDIUM = "medium"     # Recoverable errors
    HIGH = "high"         # Serious errors requiring intervention
    CRITICAL = "critical" # System failures, data loss risks


@dataclass
class ErrorContext:
    """Context information about an error."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    working_directory: str
    environment_vars: Dict[str, str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ErrorAnalysis:
    """Result of error analysis."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    primary_message: str
    secondary_messages: List[str]
    error_patterns: List[str]
    suggested_fixes: List[str]
    research_query: str
    requires_code_fix: bool
    requires_command_retry: bool
    context: ErrorContext
    confidence: float
    analysis_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'error_id': self.error_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'primary_message': self.primary_message,
            'secondary_messages': self.secondary_messages,
            'error_patterns': self.error_patterns,
            'suggested_fixes': self.suggested_fixes,
            'research_query': self.research_query,
            'requires_code_fix': self.requires_code_fix,
            'requires_command_retry': self.requires_command_retry,
            'context': self.context.to_dict(),
            'confidence': self.confidence,
            'analysis_time': self.analysis_time
        }


class ErrorClassifier:
    """
    Sophisticated error classification system using pattern matching and LLM analysis.
    
    This classifier can identify different types of errors from command output
    and provide structured analysis for recovery workflows.
    """
    
    def __init__(self, model=None):
        """
        Initialize the error classifier.
        
        Args:
            model: Language model for advanced error analysis
        """
        self.model = model
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        
        # Error pattern definitions
        self.error_patterns = self._initialize_error_patterns()
        
        # LLM analysis templates
        self.analysis_templates = self._initialize_analysis_templates()
        
        self.logger.info("ErrorClassifier initialized")
    
    def _initialize_error_patterns(self) -> Dict[ErrorCategory, List[Dict[str, Any]]]:
        """Initialize error pattern definitions for different categories."""
        return {
            ErrorCategory.CODE_ERROR: [
                {
                    'pattern': r'Traceback \(most recent call last\):',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Python traceback',
                    'extract_message': r'(\w+Error): (.+?)(?:\n|$)',
                    'research_keywords': ['python', 'traceback', 'error']
                },
                {
                    'pattern': r'SyntaxError: (.+)',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Python syntax error',
                    'extract_message': r'SyntaxError: (.+)',
                    'research_keywords': ['python', 'syntax error']
                },
                {
                    'pattern': r'ModuleNotFoundError: No module named (.+)',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Missing Python module',
                    'extract_message': r'ModuleNotFoundError: No module named (.+)',
                    'research_keywords': ['python', 'module not found', 'install package']
                },
                {
                    'pattern': r'npm ERR!',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'NPM error',
                    'extract_message': r'npm ERR! (.+)',
                    'research_keywords': ['npm', 'node', 'package manager']
                },
                {
                    'pattern': r'error: (.+)\n.*\n.*\-\-\> (.+)',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Rust compilation error',
                    'extract_message': r'error: (.+)',
                    'research_keywords': ['rust', 'compilation error', 'cargo']
                }
            ],
            
            ErrorCategory.COMMAND_SYNTAX: [
                {
                    'pattern': r'command not found',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Command not found',
                    'extract_message': r'(.+): command not found',
                    'research_keywords': ['bash', 'command not found', 'install']
                },
                {
                    'pattern': r'No such file or directory',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'File or directory not found',
                    'extract_message': r'(.+): No such file or directory',
                    'research_keywords': ['file not found', 'path']
                },
                {
                    'pattern': r'invalid option',
                    'severity': ErrorSeverity.LOW,
                    'description': 'Invalid command option',
                    'extract_message': r'(.+): invalid option',
                    'research_keywords': ['command options', 'help']
                },
                {
                    'pattern': r'usage: (.+)',
                    'severity': ErrorSeverity.LOW,
                    'description': 'Command usage error',
                    'extract_message': r'usage: (.+)',
                    'research_keywords': ['command usage', 'help']
                }
            ],
            
            ErrorCategory.SYSTEM_ERROR: [
                {
                    'pattern': r'Permission denied',
                    'severity': ErrorSeverity.HIGH,
                    'description': 'Permission denied',
                    'extract_message': r'(.+): Permission denied',
                    'research_keywords': ['permission denied', 'chmod', 'sudo']
                },
                {
                    'pattern': r'Connection refused',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Connection refused',
                    'extract_message': r'(.+): Connection refused',
                    'research_keywords': ['connection refused', 'server', 'port']
                },
                {
                    'pattern': r'Port \d+ is already in use',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Port already in use',
                    'extract_message': r'(Port \d+ is already in use)',
                    'research_keywords': ['port in use', 'kill process']
                },
                {
                    'pattern': r'No space left on device',
                    'severity': ErrorSeverity.CRITICAL,
                    'description': 'Disk space full',
                    'extract_message': r'No space left on device',
                    'research_keywords': ['disk space', 'cleanup']
                }
            ],
            
            ErrorCategory.NETWORK_ERROR: [
                {
                    'pattern': r'Could not resolve host',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'DNS resolution failure',
                    'extract_message': r'Could not resolve host: (.+)',
                    'research_keywords': ['DNS', 'network', 'host resolution']
                },
                {
                    'pattern': r'Connection timed out',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Connection timeout',
                    'extract_message': r'Connection timed out',
                    'research_keywords': ['connection timeout', 'network']
                }
            ],
            
            ErrorCategory.DEPENDENCY_ERROR: [
                {
                    'pattern': r'Package (.+) not found',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Missing package',
                    'extract_message': r'Package (.+) not found',
                    'research_keywords': ['package manager', 'install package']
                },
                {
                    'pattern': r'version conflict',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Version conflict',
                    'extract_message': r'version conflict(.+)',
                    'research_keywords': ['version conflict', 'dependency']
                }
            ],
            
            ErrorCategory.CONFIGURATION_ERROR: [
                {
                    'pattern': r'Config file not found',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Missing configuration file',
                    'extract_message': r'Config file not found: (.+)',
                    'research_keywords': ['config file', 'configuration']
                },
                {
                    'pattern': r'Invalid configuration',
                    'severity': ErrorSeverity.MEDIUM,
                    'description': 'Invalid configuration',
                    'extract_message': r'Invalid configuration: (.+)',
                    'research_keywords': ['configuration', 'config syntax']
                }
            ]
        }
    
    def _initialize_analysis_templates(self) -> Dict[str, str]:
        """Initialize LLM analysis templates."""
        return {
            'error_analysis': """Analyze this command error and provide structured information:

Command: {command}
Exit Code: {exit_code}
Error Output: {stderr}
Standard Output: {stdout}

Please provide:
1. Primary error message (concise)
2. Error category: code_error, command_syntax, system_error, network_error, dependency_error, config_error, or unknown_error
3. Severity: low, medium, high, or critical
4. 2-3 specific fix suggestions
5. Research query for finding solutions online

Analysis:""",
            
            'research_query_generation': """Generate a targeted web search query for this error:

Error: {error_message}
Command: {command}
Context: {context}

Create a search query that would find relevant solutions:
Query:"""
        }
    
    def analyze_error(self, context: ErrorContext) -> ErrorAnalysis:
        """
        Analyze an error and provide structured classification and recommendations.
        
        Args:
            context: Error context with command output and metadata
            
        Returns:
            ErrorAnalysis with classification and recommendations
        """
        analysis_start = time.time()
        error_id = self._generate_error_id(context)
        
        self.logger.info(f"Analyzing error {error_id}: {context.command}")
        
        try:
            # Step 1: Pattern-based classification
            pattern_analysis = self._classify_by_patterns(context)
            
            # Step 2: LLM-based analysis (if model available)
            if self.model:
                llm_analysis = self._analyze_with_llm(context)
                # Merge pattern and LLM analysis
                analysis = self._merge_analysis_results(pattern_analysis, llm_analysis, context)
            else:
                analysis = pattern_analysis
                analysis.confidence *= 0.8  # Reduce confidence without LLM
            
            # Step 3: Generate research query
            analysis.research_query = self._generate_research_query(analysis, context)
            
            # Step 4: Determine recovery workflow requirements
            analysis.requires_code_fix = self._requires_code_fix(analysis)
            analysis.requires_command_retry = self._requires_command_retry(analysis)
            
            analysis_time = time.time() - analysis_start
            analysis.analysis_time = analysis_time
            
            self.logger.info(f"Error analysis complete: {analysis.category.value} [{analysis.severity.value}] in {analysis_time:.3f}s")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(context, error_id, time.time() - analysis_start)
    
    def _generate_error_id(self, context: ErrorContext) -> str:
        """Generate unique error ID."""
        timestamp = int(time.time() * 1000)
        command_hash = hash(context.command) % 10000
        return f"err_{timestamp}_{command_hash}"
    
    def _classify_by_patterns(self, context: ErrorContext) -> ErrorAnalysis:
        """Classify error using pattern matching."""
        error_text = f"{context.stderr} {context.stdout}".lower()
        
        best_match = None
        best_confidence = 0.0
        
        # Check patterns for each category
        for category, patterns in self.error_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                
                if re.search(pattern, error_text, re.IGNORECASE | re.MULTILINE):
                    confidence = 0.8  # Base confidence for pattern match
                    
                    # Extract specific error messages
                    extract_pattern = pattern_info.get('extract_message')
                    if extract_pattern:
                        match = re.search(extract_pattern, error_text, re.IGNORECASE | re.MULTILINE)
                        if match:
                            confidence += 0.1
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (category, pattern_info)
        
        # Create analysis from best match
        if best_match:
            category, pattern_info = best_match
            
            # Extract primary error message
            primary_message = self._extract_primary_message(context, pattern_info)
            
            # Generate suggested fixes based on pattern
            suggested_fixes = self._generate_pattern_fixes(category, pattern_info, context)
            
            return ErrorAnalysis(
                error_id="",  # Will be set by caller
                category=category,
                severity=pattern_info['severity'],
                primary_message=primary_message,
                secondary_messages=[],
                error_patterns=[pattern_info['pattern']],
                suggested_fixes=suggested_fixes,
                research_query="",  # Will be generated later
                requires_code_fix=False,  # Will be determined later
                requires_command_retry=False,  # Will be determined later
                context=context,
                confidence=best_confidence,
                analysis_time=0.0  # Will be set by caller
            )
        else:
            # No pattern match - create unknown error analysis
            return self._create_unknown_analysis(context)
    
    def _extract_primary_message(self, context: ErrorContext, pattern_info: Dict[str, Any]) -> str:
        """Extract primary error message from context."""
        extract_pattern = pattern_info.get('extract_message')
        if extract_pattern:
            error_text = f"{context.stderr} {context.stdout}"
            match = re.search(extract_pattern, error_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        # Fallback to first line of stderr
        if context.stderr:
            return context.stderr.split('\n')[0]
        
        return f"Command failed with exit code {context.exit_code}"
    
    def _generate_pattern_fixes(self, category: ErrorCategory, pattern_info: Dict[str, Any], context: ErrorContext) -> List[str]:
        """Generate suggested fixes based on error pattern."""
        fixes = []
        
        if category == ErrorCategory.CODE_ERROR:
            if 'ModuleNotFoundError' in pattern_info['pattern']:
                module_match = re.search(r"No module named ['\"](.+?)['\"]", context.stderr)
                if module_match:
                    module_name = module_match.group(1)
                    fixes.extend([
                        f"Install missing module: pip install {module_name}",
                        f"Check if module is in requirements.txt",
                        f"Verify virtual environment is activated"
                    ])
            elif 'npm ERR!' in pattern_info['pattern']:
                fixes.extend([
                    "Clear npm cache: npm cache clean --force",
                    "Delete node_modules and reinstall: rm -rf node_modules && npm install",
                    "Check package.json for syntax errors"
                ])
        
        elif category == ErrorCategory.COMMAND_SYNTAX:
            if 'command not found' in pattern_info['pattern']:
                fixes.extend([
                    "Check if command is installed",
                    "Verify command is in PATH",
                    "Install required package or tool"
                ])
            elif 'No such file or directory' in pattern_info['pattern']:
                fixes.extend([
                    "Check file path spelling",
                    "Verify file exists in current directory",
                    "Use absolute path instead of relative path"
                ])
        
        elif category == ErrorCategory.SYSTEM_ERROR:
            if 'Permission denied' in pattern_info['pattern']:
                fixes.extend([
                    "Run with sudo if system operation required",
                    "Change file permissions: chmod +x filename",
                    "Check file ownership: chown user:group filename"
                ])
            elif 'Port' in pattern_info['pattern'] and 'in use' in pattern_info['pattern']:
                fixes.extend([
                    "Kill process using port: lsof -ti:PORT | xargs kill -9",
                    "Use different port number",
                    "Check for running services"
                ])
        
        # Generic fixes if no specific ones found
        if not fixes:
            fixes = [
                "Check command syntax and arguments",
                "Verify all dependencies are installed",
                "Review error message for specific guidance"
            ]
        
        return fixes
    
    def _create_unknown_analysis(self, context: ErrorContext) -> ErrorAnalysis:
        """Create analysis for unknown/unclassified errors."""
        # Try to extract any error message from stderr
        primary_message = context.stderr.split('\n')[0] if context.stderr else f"Command failed with exit code {context.exit_code}"
        
        return ErrorAnalysis(
            error_id="",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            primary_message=primary_message,
            secondary_messages=[],
            error_patterns=[],
            suggested_fixes=[
                "Review full error output for clues",
                "Check command documentation",
                "Search online for similar error messages"
            ],
            research_query="",
            requires_code_fix=False,
            requires_command_retry=True,
            context=context,
            confidence=0.3,
            analysis_time=0.0
        )
    
    def _analyze_with_llm(self, context: ErrorContext) -> Dict[str, Any]:
        """Analyze error using LLM for enhanced understanding."""
        try:
            prompt = self.analysis_templates['error_analysis'].format(
                command=context.command,
                exit_code=context.exit_code,
                stderr=context.stderr[:1000],  # Limit context size
                stdout=context.stdout[:500]
            )
            
            response = self.model(
                prompt,
                max_tokens=200,
                temperature=0.1,
                top_p=0.9,
                stop=["User:", "Command:", "Analysis:"]
            )
            
            analysis_text = response['choices'][0]['text'].strip()
            
            # Parse LLM response (simplified - in production would be more robust)
            return self._parse_llm_analysis(analysis_text)
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return {}
    
    def _parse_llm_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse LLM analysis response (simplified implementation)."""
        # This is a simplified parser - production version would be more robust
        lines = analysis_text.split('\n')
        
        result = {
            'primary_message': '',
            'category': 'unknown_error',
            'severity': 'medium',
            'suggested_fixes': []
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('1.'):
                result['primary_message'] = line[2:].strip()
            elif line.startswith('2.'):
                category = line[2:].strip().lower()
                if category in [c.value for c in ErrorCategory]:
                    result['category'] = category
            elif line.startswith('3.'):
                severity = line[2:].strip().lower()
                if severity in [s.value for s in ErrorSeverity]:
                    result['severity'] = severity
            elif line.startswith('4.') or line.startswith('-'):
                fix = line[2:].strip() if line.startswith('4.') else line[1:].strip()
                if fix:
                    result['suggested_fixes'].append(fix)
        
        return result
    
    def _merge_analysis_results(self, pattern_analysis: ErrorAnalysis, llm_analysis: Dict[str, Any], context: ErrorContext) -> ErrorAnalysis:
        """Merge pattern-based and LLM analysis results."""
        # Use LLM analysis to enhance pattern analysis
        if llm_analysis.get('primary_message'):
            pattern_analysis.primary_message = llm_analysis['primary_message']
        
        if llm_analysis.get('suggested_fixes'):
            # Merge suggested fixes, prioritizing LLM suggestions
            pattern_analysis.suggested_fixes = llm_analysis['suggested_fixes'] + pattern_analysis.suggested_fixes
            # Remove duplicates while preserving order
            seen = set()
            unique_fixes = []
            for fix in pattern_analysis.suggested_fixes:
                if fix not in seen:
                    seen.add(fix)
                    unique_fixes.append(fix)
            pattern_analysis.suggested_fixes = unique_fixes[:5]  # Limit to top 5
        
        # Increase confidence when both methods agree
        pattern_analysis.confidence = min(0.95, pattern_analysis.confidence + 0.1)
        
        return pattern_analysis
    
    def _generate_research_query(self, analysis: ErrorAnalysis, context: ErrorContext) -> str:
        """Generate targeted research query for error."""
        # Extract key terms from error message
        error_terms = self._extract_key_terms(analysis.primary_message)
        
        # Get command name
        command_name = context.command.split()[0] if context.command else ""
        
        # Build research query
        query_parts = []
        
        if command_name:
            query_parts.append(command_name)
        
        query_parts.extend(error_terms[:3])  # Top 3 error terms
        
        # Add category-specific terms
        if analysis.category == ErrorCategory.CODE_ERROR:
            query_parts.append("fix")
        elif analysis.category == ErrorCategory.COMMAND_SYNTAX:
            query_parts.append("usage example")
        elif analysis.category == ErrorCategory.SYSTEM_ERROR:
            query_parts.append("solution")
        
        return " ".join(query_parts)
    
    def _extract_key_terms(self, message: str) -> List[str]:
        """Extract key terms from error message."""
        # Remove common noise words
        noise_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Split and clean terms
        terms = re.findall(r'\b\w+\b', message.lower())
        key_terms = [term for term in terms if term not in noise_words and len(term) > 2]
        
        return key_terms[:5]  # Return top 5 terms
    
    def _requires_code_fix(self, analysis: ErrorAnalysis) -> bool:
        """Determine if error requires code modification."""
        code_fix_categories = {ErrorCategory.CODE_ERROR}
        code_fix_patterns = ['traceback', 'syntaxerror', 'compilation error', 'build failed']
        
        if analysis.category in code_fix_categories:
            return True
        
        for pattern in code_fix_patterns:
            if pattern in analysis.primary_message.lower():
                return True
        
        return False
    
    def _requires_command_retry(self, analysis: ErrorAnalysis) -> bool:
        """Determine if error can be fixed by retrying with corrected command."""
        retry_categories = {ErrorCategory.COMMAND_SYNTAX, ErrorCategory.DEPENDENCY_ERROR, ErrorCategory.CONFIGURATION_ERROR}
        
        if analysis.category in retry_categories:
            return True
        
        # Low severity errors are often fixable by retry
        if analysis.severity == ErrorSeverity.LOW:
            return True
        
        return False
    
    def _create_fallback_analysis(self, context: ErrorContext, error_id: str, analysis_time: float) -> ErrorAnalysis:
        """Create fallback analysis when main analysis fails."""
        return ErrorAnalysis(
            error_id=error_id,
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.MEDIUM,
            primary_message=f"Analysis failed for command: {context.command}",
            secondary_messages=[],
            error_patterns=[],
            suggested_fixes=["Manual review required"],
            research_query=f"{context.command} error troubleshooting",
            requires_code_fix=False,
            requires_command_retry=False,
            context=context,
            confidence=0.1,
            analysis_time=analysis_time
        )


# Convenience function
def create_error_classifier(model=None) -> ErrorClassifier:
    """Create error classifier instance."""
    return ErrorClassifier(model=model)


# Example usage and testing
if __name__ == "__main__":
    classifier = create_error_classifier()
    
    # Test error classification
    test_context = ErrorContext(
        command="python app.py",
        exit_code=1,
        stdout="",
        stderr="Traceback (most recent call last):\n  File \"app.py\", line 10, in <module>\nModuleNotFoundError: No module named 'flask'",
        execution_time=0.5,
        working_directory="/home/user/project",
        environment_vars={},
        timestamp=datetime.now()
    )
    
    analysis = classifier.analyze_error(test_context)
    
    print("🔍 Error Analysis Test")
    print("=" * 50)
    print(f"Category: {analysis.category.value}")
    print(f"Severity: {analysis.severity.value}")
    print(f"Message: {analysis.primary_message}")
    print(f"Fixes: {analysis.suggested_fixes}")
    print(f"Research Query: {analysis.research_query}")
    print(f"Confidence: {analysis.confidence:.2f}")