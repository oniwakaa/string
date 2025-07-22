"""
WebResearcherAgent - AI-powered web scraping agent using ScrapeGraphAI and Ollama.

This agent acts as an intelligent wrapper around ScrapeGraphAI, configured to use
a local Ollama instance running the WebSailor-3B model. It provides structured
web research capabilities for the multi-agent system.
"""

import asyncio
import traceback
from typing import Any, Dict

from agents.base import BaseAgent, Task, Result
from scrapegraphai.graphs import SmartScraperGraph


class WebResearcherAgent(BaseAgent):
    """
    Web research agent that extracts structured information from web pages.
    
    This agent uses ScrapeGraphAI with a local Ollama model to intelligently
    scrape and extract information from web pages based on user prompts.
    """
    
    def __init__(self):
        """Initialize the WebResearcherAgent."""
        super().__init__(
            name="WebSailor-3B-Researcher", 
            role="web_researcher",
            model_name=None  # Uses Ollama, not HuggingFace models
        )
        
        # Configure ScrapeGraphAI to use local Ollama models
        self.graph_config = {
            "llm": {
                "model": "ollama/qwen3:0.6b",  # Using smaller, faster model for testing
                "temperature": 0,
                "format": "json",
                "base_url": "http://127.0.0.1:11434",
                "model_tokens": 8192,  # Specify token limit to avoid warnings
            },
            "embeddings": {
                "model": "ollama/nomic-embed-text",
                "base_url": "http://127.0.0.1:11434",
            },
        }
        
    async def execute(self, task: Task) -> Result:
        """
        Execute web research task using ScrapeGraphAI.
        
        Args:
            task: Task object containing:
                - prompt: What information to extract from the web page
                - context: Must contain 'source_url' key with the URL to scrape
                
        Returns:
            Result: Contains extracted structured data or error information
        """
        try:
            # Validate input
            if not task.context or "source_url" not in task.context:
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output={},
                    error_message="Missing required 'source_url' in task context"
                )
                
            source_url = task.context["source_url"]
            
            # Set agent status
            self.status = 'processing'
            
            # Create SmartScraperGraph instance
            smart_scraper_graph = SmartScraperGraph(
                prompt=task.prompt,
                source=source_url,
                config=self.graph_config
            )
            
            # Run the scraping operation in a separate thread to avoid blocking
            scraping_result = await asyncio.to_thread(smart_scraper_graph.run)
            
            # Reset agent status
            self.status = 'ready'
            
            return Result(
                task_id=task.task_id,
                status="success",
                output={
                    "extracted_data": scraping_result,
                    "source_url": source_url,
                    "extraction_prompt": task.prompt
                }
            )
            
        except Exception as e:
            self.status = 'error'
            error_msg = f"Web scraping failed: {str(e)}"
            
            # Log the full traceback for debugging
            print(f"❌ WebResearcherAgent error: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            
            return Result(
                task_id=task.task_id,
                status="failure", 
                output={},
                error_message=error_msg
            )
    
    def lazy_load_model(self):
        """
        Override base class method since this agent uses Ollama, not HuggingFace models.
        
        The agent relies on the local Ollama service being available and having
        the required models (websailor-local and nomic-embed-text) installed.
        """
        try:
            # Test connection to Ollama
            import ollama
            
            # Check if required models are available
            models_response = ollama.list()
            model_names = [model.model for model in models_response.models]
            
            required_models = ['qwen3:0.6b', 'nomic-embed-text:latest']
            missing_models = [model for model in required_models if model not in model_names]
            
            if missing_models:
                raise RuntimeError(f"Missing required Ollama models: {missing_models}")
            
            self.status = 'ready'
            print(f"✅ WebResearcherAgent ready - Ollama models verified")
            
        except Exception as e:
            self.status = 'error'
            error_msg = f"Failed to verify Ollama models: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)