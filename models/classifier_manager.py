"""
Isolated Classifier Manager - Gemma-only model loading.
Prevents resource contention with main ModelManager.
"""

import os
import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

def _get_string_home() -> Path:
    """Resolve STRING_HOME path cross-platform."""
    if "STRING_HOME" in os.environ:
        return Path(os.environ["STRING_HOME"]).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("USERPROFILE", str(Path.home())))
        return (base / ".string").resolve()
    return (Path.home() / ".string").resolve()

class ClassifierManager:
    """
    Isolated classifier manager for Gemma model only.
    Prevents shared state conflicts with main ModelManager.
    """
    
    def __init__(self):
        self.string_home = _get_string_home()
        self.model_name = os.getenv("STRING_CLASSIFIER_MODEL_NAME", "Gemma-3-270m-it-classifier")
        self.model = None
        self._lock = threading.RLock()
        self._ready = False
        self.model_config = self._load_model_config()
        
    def _load_model_config(self) -> Dict[str, Any]:
        """Load Gemma model configuration from STRING_HOME manifest."""
        manifest_path = self.string_home / "config" / "models.json"
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Find classifier model in manifest by name match
            for model_entry in manifest.get("models", []):
                model_name = model_entry.get("name", "")
                if model_name == self.model_name:
                    models_dir = self.string_home / "models"
                    local_dir = model_entry.get("local_dir", "")
                    filename = model_entry.get("filename", "")
                    
                    if local_dir and filename:
                        model_path = (models_dir / local_dir / filename).as_posix()
                        
                        return {
                            "path": model_path,
                            "n_ctx": 16384,
                            "n_gpu_layers": 0,  # Run on CPU by default to avoid GPU pressure
                            "n_batch": 512,
                            "n_threads": 8,
                            "verbose": False
                        }
            
            # Fallback if not found in manifest
            logger.warning(f"Classifier model {self.model_name} not found in manifest, using fallback path")
            if "270m" in self.model_name.lower():
                # New 270M model fallback
                fallback_path = self.string_home / "models" / "gemma-3-270m-it" / "gemma-3-270m-it-Q4_K_S.gguf"
            else:
                # Original gemma-3n-E4B-it fallback for rollback compatibility
                fallback_path = self.string_home / "models" / "gemma-3n-E4B-it" / "gemma-3n-E4B-it-Q5_K_S.gguf"
            
            return {
                "path": fallback_path.as_posix(),
                "n_ctx": 16384,
                "n_gpu_layers": 0,  # Run on CPU by default
                "n_batch": 512,
                "n_threads": 8,
                "verbose": False
            }
            
        except Exception as e:
            logger.error(f"Failed to load model config: {e}")
            raise RuntimeError(f"Could not configure Gemma model: {e}")
    
    def load_model(self):
        """Load Gemma model for classification."""
        with self._lock:
            if self.model is not None:
                logger.info("Gemma model already loaded")
                return
            
            if Llama is None:
                raise RuntimeError("llama-cpp-python not available for GGUF models")
            
            model_path = self.model_config["path"]
            
            # Ensure model file exists
            if not os.path.exists(model_path):
                raise RuntimeError(
                    f"Gemma model file not found: {model_path}. "
                    f"Ensure models are installed under {self.string_home}/models"
                )
            
            logger.info(f"Loading Gemma model from: {model_path}")
            start_time = time.time()
            
            try:
                self.model = Llama(
                    model_path=model_path,
                    n_ctx=self.model_config["n_ctx"],
                    n_batch=self.model_config["n_batch"],
                    n_threads=self.model_config["n_threads"],
                    n_gpu_layers=self.model_config["n_gpu_layers"],
                    verbose=self.model_config["verbose"]
                )
                
                load_time = time.time() - start_time
                logger.info(f"Gemma model loaded successfully in {load_time:.2f}s")
                
                # Test basic functionality without decode
                self._ready = True
                
            except Exception as e:
                logger.error(f"Failed to load Gemma model: {e}")
                raise RuntimeError(f"Gemma model loading failed: {e}")
    
    def is_ready(self) -> bool:
        """Check if classifier is ready for inference."""
        return self._ready and self.model is not None
    
    def get_context_size(self) -> int:
        """Get model context size."""
        return self.model_config.get("n_ctx", 16384)
    
    def classify(self, text: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify intent using loaded Gemma model.
        
        Args:
            text: Input text to classify
            project_id: Optional project context
            
        Returns:
            Dict with 'intent' and 'confidence' keys
        """
        if not self.is_ready():
            raise RuntimeError("Classifier not ready")
        
        with self._lock:
            try:
                # Minimal classification prompt (reuse from main classifier)
                prompt = f"""Classify user request into ONE intent:

web_research: Get info from external websites/sources (NOT create internal docs)
codebase_query: Understand existing code logic (NOT quality evaluation)  
code_generation: Create new code from scratch (NOT modify existing)
code_editing: Change/modify/fix code files (NOT just identify issues)
code_analysis: Evaluate code quality/structure (NOT understand logic)
documentation: Create internal docs/comments (NOT fetch external docs)
tool_execution: Run/execute/perform actions that produce output (NOT passive review)

Request: {text}

Intent:"""
                
                # Generate classification
                response = self.model(
                    prompt,
                    max_tokens=20,
                    temperature=0.1,
                    top_p=0.9,
                    stop=["User:", "Intent:", "Categories:", "\\n\\n"]
                )
                
                # Extract intent from response
                classification_text = response['choices'][0]['text'].strip()
                intent = self._extract_intent(classification_text)
                
                # Set confidence based on match quality
                confidence = 0.9 if intent != 'general_query' else 0.3
                
                return {
                    "intent": intent,
                    "confidence": confidence
                }
                
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                # Return fallback classification
                return {
                    "intent": "general_query",
                    "confidence": 0.1
                }
    
    def _extract_intent(self, text: str) -> str:
        """Extract intent from model response."""
        text_lower = text.lower().strip()
        
        # Known intents
        intents = [
            "web_research", "codebase_query", "code_generation", 
            "code_editing", "code_analysis", "documentation", "tool_execution"
        ]
        
        # Direct intent matching
        for intent in intents:
            if intent.lower() in text_lower:
                return intent
        
        # Partial matching with underscores replaced
        for intent in intents:
            intent_words = intent.replace("_", " ").lower()
            if intent_words in text_lower:
                return intent
        
        # Keyword-based fallback
        if any(term in text_lower for term in ["scrape", "fetch", "web", "website", "url"]):
            return "web_research"
        elif any(term in text_lower for term in ["find", "search", "where", "locate", "show"]):
            return "codebase_query"
        elif any(term in text_lower for term in ["create", "generate", "build", "implement", "write"]):
            return "code_generation"
        elif any(term in text_lower for term in ["edit", "fix", "modify", "update", "change", "refactor"]):
            return "code_editing"
        elif any(term in text_lower for term in ["analyze", "review", "check", "audit", "quality"]):
            return "code_analysis"
        elif any(term in text_lower for term in ["document", "explain", "describe", "usage"]):
            return "documentation"
        
        return "general_query"
    
    def shutdown(self):
        """Shutdown the classifier and clean up resources."""
        with self._lock:
            if self.model and hasattr(self.model, 'close'):
                try:
                    self.model.close()
                except Exception as e:
                    logger.warning(f"Error closing model: {e}")
            
            self.model = None
            self._ready = False
            logger.info("Classifier manager shutdown complete")