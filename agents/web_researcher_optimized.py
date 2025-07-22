"""
High-Performance WebResearcherAgent - Optimized for speed and efficiency.

This agent implements multiple performance optimizations:
- Connection pooling and session reuse
- Parallel processing with semaphore-based rate limiting
- Fast HTML parsing with lxml
- Intelligent caching system
- Batched LLM inference
- Targeted content extraction
"""

import asyncio
import aiohttp
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import hashlib
from lxml import html, etree
from lxml_html_clean import Cleaner
import json
import ollama

from agents.base import BaseAgent, Task, Result


@dataclass
class CacheEntry:
    """Cache entry for scraped content."""
    content: str
    timestamp: float
    url: str
    content_hash: str
    

class PerformanceOptimizedWebResearcher(BaseAgent):
    """
    High-performance web research agent with multiple optimizations.
    
    Key optimizations:
    1. Async HTTP with connection pooling
    2. Fast lxml-based HTML parsing
    3. Intelligent content caching
    4. Parallel processing with rate limiting
    5. Batched LLM inference
    6. Targeted content extraction
    """
    
    def __init__(self, max_concurrent_requests: int = 10, cache_ttl: int = 3600):
        """Initialize the optimized web researcher."""
        super().__init__(
            name="HighPerf-WebResearcher", 
            role="web_researcher",
            model_name=None
        )
        
        # Performance configuration
        self.max_concurrent_requests = max_concurrent_requests
        self.cache_ttl = cache_ttl
        
        # HTTP session with connection pooling
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Content cache
        self.content_cache: Dict[str, CacheEntry] = {}
        
        # HTML cleaner for efficient parsing
        self.html_cleaner = Cleaner(
            scripts=True,
            javascript=True,
            comments=True,
            style=True,
            links=False,
            meta=False,
            page_structure=False,
            processing_instructions=True,
            embedded=True,
            frames=True,
            forms=False,
            remove_unknown_tags=False,
            safe_attrs_only=False,
        )
        
        # Ollama client
        self.ollama_client = ollama.AsyncClient()
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with optimized settings."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(
                total=30,
                connect=10,
                sock_read=20
            )
            
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection limit
                limit_per_host=20,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            headers = {
                'User-Agent': 'HighPerf-WebResearcher/1.0 (+https://example.com/bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
        
        return self.session
    
    def _extract_content_fast(self, html_content: str, url: str) -> Dict[str, Any]:
        """Fast content extraction using lxml."""
        try:
            # Parse HTML - handle encoding issues
            if isinstance(html_content, str):
                html_content = html_content.encode('utf-8')
            doc = html.fromstring(html_content)
            
            # Clean the document
            cleaned_doc = self.html_cleaner.clean_html(doc)
            
            # Extract key elements efficiently
            content = {
                'title': '',
                'headings': [],
                'paragraphs': [],
                'lists': [],
                'links': [],
                'meta_description': '',
                'text_content': ''
            }
            
            # Title
            title_elem = cleaned_doc.find('.//title')
            if title_elem is not None:
                content['title'] = (title_elem.text or '').strip()
            
            # Meta description
            meta_desc = cleaned_doc.find('.//meta[@name="description"]')
            if meta_desc is not None:
                content['meta_description'] = meta_desc.get('content', '').strip()
            
            # Headings (h1-h6)
            for level in range(1, 7):
                headings = cleaned_doc.xpath(f'//h{level}')
                for h in headings:
                    text = (h.text_content() or '').strip()
                    if text:
                        content['headings'].append({
                            'level': level,
                            'text': text
                        })
            
            # Paragraphs
            paragraphs = cleaned_doc.xpath('//p')
            for p in paragraphs:
                text = (p.text_content() or '').strip()
                if text and len(text) > 20:  # Filter out very short paragraphs
                    content['paragraphs'].append(text)
            
            # Lists
            lists = cleaned_doc.xpath('//ul | //ol')
            for lst in lists:
                items = [li.text_content().strip() for li in lst.xpath('.//li')]
                items = [item for item in items if item]  # Filter empty items
                if items:
                    content['lists'].append(items)
            
            # Links
            links = cleaned_doc.xpath('//a[@href]')
            for link in links[:20]:  # Limit to first 20 links
                href = link.get('href', '')
                text = (link.text_content() or '').strip()
                if href and text:
                    full_url = urljoin(url, href)
                    content['links'].append({
                        'url': full_url,
                        'text': text
                    })
            
            # Full text content
            content['text_content'] = cleaned_doc.text_content().strip()
            
            return content
            
        except Exception as e:
            print(f"⚠️ Fast content extraction failed: {e}")
            # Fallback to simple text extraction
            try:
                doc = html.fromstring(html_content)
                return {
                    'title': '',
                    'text_content': doc.text_content().strip(),
                    'error': str(e)
                }
            except:
                return {'error': f'Content extraction failed: {e}'}
    
    def _get_cache_key(self, url: str, prompt: str) -> str:
        """Generate cache key for URL and prompt combination."""
        combined = f"{url}:{prompt}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - cache_entry.timestamp) < self.cache_ttl
    
    async def _fetch_content(self, url: str) -> Tuple[str, bool]:
        """Fetch content with caching and error handling."""
        # Check content cache (URL-based)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in self.content_cache:
            cache_entry = self.content_cache[url_hash]
            if self._is_cache_valid(cache_entry):
                print(f"🎯 Cache hit for {url}")
                return cache_entry.content, True
        
        # Fetch from web
        async with self.semaphore:  # Rate limiting
            try:
                session = await self._get_session()
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Cache the content
                        self.content_cache[url_hash] = CacheEntry(
                            content=content,
                            timestamp=time.time(),
                            url=url,
                            content_hash=hashlib.md5(content.encode()).hexdigest()
                        )
                        
                        return content, False
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                        
            except Exception as e:
                raise Exception(f"Failed to fetch {url}: {str(e)}")
    
    async def _process_with_llm(self, extracted_content: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Process extracted content with LLM for intelligent analysis."""
        try:
            # Create a focused context for the LLM
            context_parts = []
            
            if extracted_content.get('title'):
                context_parts.append(f"Title: {extracted_content['title']}")
            
            if extracted_content.get('meta_description'):
                context_parts.append(f"Description: {extracted_content['meta_description']}")
            
            if extracted_content.get('headings'):
                headings_text = "\n".join([f"H{h['level']}: {h['text']}" for h in extracted_content['headings'][:5]])
                context_parts.append(f"Headings:\n{headings_text}")
            
            if extracted_content.get('paragraphs'):
                # Use first few paragraphs to avoid token limits
                paragraphs_text = "\n".join(extracted_content['paragraphs'][:3])
                context_parts.append(f"Content:\n{paragraphs_text}")
            
            context = "\n\n".join(context_parts)
            
            # Limit context length to avoid token issues
            if len(context) > 2000:
                context = context[:2000] + "..."
            
            # Craft efficient prompt
            llm_prompt = f"""Based on this web page content, {prompt}

Content:
{context}

Provide a concise, structured response in JSON format."""
            
            # Call Ollama async
            response = await self.ollama_client.chat(
                model='qwen3:0.6b',
                messages=[
                    {
                        'role': 'user',
                        'content': llm_prompt
                    }
                ],
                options={
                    'temperature': 0,
                    'num_predict': 512,  # Limit response length
                }
            )
            
            llm_result = response['message']['content']
            
            return {
                'raw_content': extracted_content,
                'llm_analysis': llm_result,
                'processing_method': 'llm_enhanced'
            }
            
        except Exception as e:
            print(f"⚠️ LLM processing failed: {e}")
            # Fallback to raw content
            return {
                'raw_content': extracted_content,
                'llm_analysis': f"LLM processing failed: {e}",
                'processing_method': 'raw_fallback'
            }
    
    async def execute(self, task: Task) -> Result:
        """Execute optimized web research task."""
        try:
            # Validate input
            if not task.context or "source_url" not in task.context:
                return Result(
                    task_id=task.task_id,
                    status="failure",
                    output={},
                    error_message="Missing required 'source_url' in task context"
                )
            
            url = task.context["source_url"]
            self.status = 'processing'
            
            start_time = time.time()
            
            # Step 1: Fetch content (with caching and rate limiting)
            html_content, from_cache = await self._fetch_content(url)
            fetch_time = time.time() - start_time
            
            # Step 2: Fast content extraction
            extract_start = time.time()
            extracted_content = self._extract_content_fast(html_content, url)
            extract_time = time.time() - extract_start
            
            # Step 3: LLM processing (optional, based on prompt complexity)
            llm_start = time.time()
            if any(keyword in task.prompt.lower() for keyword in ['analyze', 'summary', 'extract specific', 'understand']):
                final_result = await self._process_with_llm(extracted_content, task.prompt)
            else:
                # Simple extraction without LLM
                final_result = {
                    'raw_content': extracted_content,
                    'processing_method': 'fast_extraction_only'
                }
            llm_time = time.time() - llm_start
            
            total_time = time.time() - start_time
            
            self.status = 'ready'
            
            return Result(
                task_id=task.task_id,
                status="success",
                output={
                    'extracted_data': final_result,
                    'source_url': url,
                    'extraction_prompt': task.prompt,
                    'performance_metrics': {
                        'total_time': total_time,
                        'fetch_time': fetch_time,
                        'extract_time': extract_time,
                        'llm_time': llm_time,
                        'from_cache': from_cache
                    }
                }
            )
            
        except Exception as e:
            self.status = 'error'
            error_msg = f"Optimized web scraping failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return Result(
                task_id=task.task_id,
                status="failure",
                output={},
                error_message=error_msg
            )
    
    async def execute_batch(self, tasks: List[Task]) -> List[Result]:
        """Execute multiple tasks in parallel with optimal batching."""
        if not tasks:
            return []
        
        print(f"🚀 Processing {len(tasks)} tasks in parallel")
        
        # Process all tasks concurrently
        results = await asyncio.gather(
            *[self.execute(task) for task in tasks],
            return_exceptions=True
        )
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(Result(
                    task_id=tasks[i].task_id,
                    status="failure",
                    output={},
                    error_message=f"Batch execution failed: {str(result)}"
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def lazy_load_model(self):
        """Initialize the optimized web researcher."""
        try:
            # Verify Ollama connection
            import ollama
            models_response = ollama.list()
            model_names = [model.model for model in models_response.models]
            
            if 'qwen3:0.6b' not in model_names:
                raise RuntimeError("Missing required Ollama model: qwen3:0.6b")
            
            self.status = 'ready'
            print(f"✅ {self.name} ready - Optimized for high-performance web research")
            
        except Exception as e:
            self.status = 'error'
            error_msg = f"Failed to initialize optimized web researcher: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        
        # Clear cache
        self.content_cache.clear()
    
    def __del__(self):
        """Ensure cleanup on destruction."""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            try:
                asyncio.create_task(self.cleanup())
            except:
                pass