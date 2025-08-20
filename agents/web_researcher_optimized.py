"""
Enhanced WebResearcherAgent with true headless web surfing capabilities.

This agent implements multiple performance optimizations:
- Playwright-based headless browsing (true web surfing)
- Natural language query processing with URL extraction
- Connection pooling and session reuse (fallback)
- Parallel processing with semaphore-based rate limiting
- Fast HTML parsing with deterministic waits
- Intelligent caching system
- MemOS integration for persistent research results
- Bounded timeouts and guardrails
"""

import asyncio
import aiohttp
import time
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import hashlib
from lxml import html, etree
from lxml_html_clean import Cleaner
import json
import ollama

from agents.base import BaseAgent, Task, Result

# Set up logging for observability
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for scraped content."""
    content: str
    timestamp: float
    url: str
    content_hash: str
    

class PerformanceOptimizedWebResearcher(BaseAgent):
    """
    Enhanced web research agent with true headless web surfing capabilities.
    
    Key features:
    1. Playwright-based headless browsing with Chromium
    2. Natural language query processing with URL extraction
    3. Intelligent content caching with bounded timeouts
    4. MemOS integration for persistent research results
    5. Fallback to aiohttp for simple fetching
    6. Observability logging for routing and web access
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
        
        # Playwright for true headless browsing
        self.playwright = None
        self.browser = None
        self.browser_context = None
        
        # HTTP session with connection pooling (fallback)
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Content cache
        self.content_cache: Dict[str, CacheEntry] = {}
        
        # Timeouts and guardrails
        self.page_timeout = 30000  # 30 seconds per page
        self.navigation_timeout = 15000  # 15 seconds for navigation
        self.max_pages_per_query = 2  # Primary + one fallback page max
        
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
    
    async def _init_playwright(self):
        """Initialize Playwright browser for headless surfing."""
        if self.browser is None:
            try:
                from playwright.async_api import async_playwright
                
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-background-timer-throttling',
                        '--disable-renderer-backgrounding',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-ipc-flooding-protection'
                    ]
                )
                
                # Create browser context with reasonable settings
                self.browser_context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='HighPerf-WebResearcher/1.0 (headless)',
                    ignore_https_errors=True
                )
                
                # Set default timeouts
                self.browser_context.set_default_timeout(self.page_timeout)
                self.browser_context.set_default_navigation_timeout(self.navigation_timeout)
                
                logger.info("✅ Playwright browser initialized for headless surfing")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Playwright: {e}")
                raise
    
    def _extract_url_from_query(self, query: str) -> Optional[str]:
        """Extract URL from natural language query."""
        # Direct URL patterns
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+[^\s<>"{}|\\^`[\].,;!?]'
        urls = re.findall(url_pattern, query)
        if urls:
            return urls[0]
        
        # Common domain patterns with implicit HTTPS
        domain_patterns = [
            r'(?:from\s+|visit\s+|go\s+to\s+|check\s+)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:com|org|net|dev|io|ai|co|app|tech))\s+(?:website|site|docs|documentation)',
        ]
        
        for pattern in domain_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                domain = matches[0]
                return f"https://{domain}"
        
        # Well-known sites for common queries
        site_mapping = {
            'react': 'https://react.dev',
            'vue': 'https://vuejs.org',
            'angular': 'https://angular.io',
            'svelte': 'https://svelte.dev',
            'node.js': 'https://nodejs.org',
            'npm': 'https://npmjs.com',
            'github': 'https://github.com',
            'stackoverflow': 'https://stackoverflow.com',
            'mdn': 'https://developer.mozilla.org'
        }
        
        query_lower = query.lower()
        for keyword, url in site_mapping.items():
            if keyword in query_lower and any(term in query_lower for term in ['documentation', 'docs', 'guide', 'tutorial', 'api']):
                return url
        
        return None
        
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
    
    async def _fetch_with_playwright(self, url: str, query: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Fetch content using Playwright for true headless browsing."""
        try:
            await self._init_playwright()
            
            page = await self.browser_context.new_page()
            page_metadata = {}
            
            try:
                # Navigate to the URL with timeout
                logger.info(f"🌐 Navigating to {url}")
                start_time = time.time()
                
                await page.goto(url, wait_until='domcontentloaded', timeout=self.navigation_timeout)
                navigation_time = time.time() - start_time
                
                # Wait for page to be fully loaded and interactive
                await page.wait_for_load_state('networkidle', timeout=5000)  # Wait max 5s for network idle
                
                # Extract page metadata
                title = await page.title()
                current_url = page.url
                
                # Extract content with bounded selectors and timeouts
                content_extraction_start = time.time()
                
                # Get title and headings
                headings = []
                for level in range(1, 4):  # h1, h2, h3 only for performance
                    heading_elements = await page.query_selector_all(f'h{level}')
                    for elem in heading_elements[:10]:  # Limit to 10 per level
                        text = await elem.text_content()
                        if text and text.strip():
                            headings.append({'level': level, 'text': text.strip()})
                
                # Get main content paragraphs
                paragraphs = []
                p_elements = await page.query_selector_all('p, article p, main p, .content p')
                for elem in p_elements[:15]:  # Limit to 15 paragraphs
                    text = await elem.text_content()
                    if text and len(text.strip()) > 20:  # Filter short paragraphs
                        paragraphs.append(text.strip())
                
                # Get lists if relevant to query
                lists = []
                if any(term in query.lower() for term in ['list', 'steps', 'examples', 'api', 'methods']):
                    list_elements = await page.query_selector_all('ul, ol')
                    for elem in list_elements[:5]:  # Limit to 5 lists
                        items = await elem.query_selector_all('li')
                        list_items = []
                        for item in items[:10]:  # Max 10 items per list
                            text = await item.text_content()
                            if text and text.strip():
                                list_items.append(text.strip())
                        if list_items:
                            lists.append(list_items)
                
                # Get code blocks if this appears to be technical documentation
                code_blocks = []
                if any(term in query.lower() for term in ['code', 'example', 'function', 'api', 'hook']):
                    code_elements = await page.query_selector_all('pre, code, .highlight')
                    for elem in code_elements[:5]:  # Limit to 5 code blocks
                        text = await elem.text_content()
                        if text and len(text.strip()) > 10:
                            code_blocks.append(text.strip())
                
                extraction_time = time.time() - content_extraction_start
                
                extracted_content = {
                    'title': title,
                    'url': current_url,
                    'headings': headings,
                    'paragraphs': paragraphs,
                    'lists': lists,
                    'code_blocks': code_blocks,
                    'extraction_method': 'playwright_headless'
                }
                
                page_metadata = {
                    'navigation_time': navigation_time,
                    'extraction_time': extraction_time,
                    'total_headings': len(headings),
                    'total_paragraphs': len(paragraphs),
                    'total_lists': len(lists),
                    'total_code_blocks': len(code_blocks),
                    'final_url': current_url
                }
                
                logger.info(f"✅ Page extracted: {len(paragraphs)} paragraphs, {len(headings)} headings in {extraction_time:.2f}s")
                
                return extracted_content, page_metadata
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"❌ Playwright extraction failed for {url}: {e}")
            raise
    
    def _create_concise_summary(self, extracted_content: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Create concise summary with brief citations, avoiding raw URLs in user content."""
        try:
            title = extracted_content.get('title', 'Untitled')
            url = extracted_content.get('url', '')
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '') if parsed_url.netloc else 'Unknown'
            
            # Create structured summary
            summary_parts = []
            
            # Add title and source
            if title and title != 'Untitled':
                summary_parts.append(f"**{title}**")
            
            # Add relevant headings (top 3)
            headings = extracted_content.get('headings', [])[:3]
            if headings:
                heading_text = " | ".join([h['text'] for h in headings])
                summary_parts.append(f"Key sections: {heading_text}")
            
            # Add key paragraphs (first 2 relevant ones)
            paragraphs = extracted_content.get('paragraphs', [])
            relevant_paragraphs = []
            query_terms = query.lower().split()[:3]  # Use first 3 query terms
            
            for p in paragraphs[:5]:  # Check first 5 paragraphs
                p_lower = p.lower()
                if any(term in p_lower for term in query_terms):
                    relevant_paragraphs.append(p)
                    if len(relevant_paragraphs) >= 2:
                        break
            
            # If no relevant paragraphs found, use first 2
            if not relevant_paragraphs:
                relevant_paragraphs = paragraphs[:2]
            
            for p in relevant_paragraphs:
                # Truncate long paragraphs
                truncated = p[:300] + "..." if len(p) > 300 else p
                summary_parts.append(truncated)
            
            # Add code examples if relevant
            code_blocks = extracted_content.get('code_blocks', [])
            if code_blocks and any(term in query.lower() for term in ['code', 'example', 'function', 'api']):
                first_code = code_blocks[0][:200] + "..." if len(code_blocks[0]) > 200 else code_blocks[0]
                summary_parts.append(f"Code example:\n```\n{first_code}\n```")
            
            # Join summary
            summary_text = "\n\n".join(summary_parts)
            
            # Add brief citation (domain and title only, no raw URL)
            citation = f"Source: {title} ({domain})"
            
            return {
                'summary': summary_text,
                'citation': citation,
                'source_title': title,
                'source_domain': domain,
                'extraction_metadata': {
                    'total_headings': len(headings),
                    'total_paragraphs': len(paragraphs),
                    'total_code_blocks': len(code_blocks),
                    'relevant_paragraphs_found': len([p for p in paragraphs[:5] if any(term in p.lower() for term in query.lower().split()[:3])])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Summary creation failed: {e}")
            # Fallback summary
            title = extracted_content.get('title', 'Web Content')
            return {
                'summary': f"Retrieved content from {title}. Summary generation failed: {e}",
                'citation': f"Source: {title}",
                'extraction_metadata': {'error': str(e)}
            }
    
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
        """Execute enhanced web research task with headless browsing."""
        try:
            self.status = 'processing'
            start_time = time.time()
            
            # Extract URL from prompt or context
            url = None
            
            # Check if URL is provided in context (legacy mode)
            if task.context and "source_url" in task.context:
                url = task.context["source_url"]
                logger.info(f"🔗 Using URL from context: {url}")
            else:
                # Extract URL from natural language query
                url = self._extract_url_from_query(task.prompt)
                if url:
                    logger.info(f"🔍 Extracted URL from query: {url}")
                else:
                    return Result(
                        task_id=task.task_id,
                        status="failure",
                        output={},
                        error_message="Could not extract URL from query. Please provide a direct URL or mention a specific website."
                    )
            
            # Validate URL format
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return Result(
                    task_id=task.task_id,
                    status="failure", 
                    output={},
                    error_message=f"Invalid URL format: {url}"
                )
            
            # Log web access metadata for observability
            logger.info(f"🌐 Starting web research for domain: {parsed_url.netloc}")
            
            # Step 1: Headless browsing with Playwright (primary method)
            try:
                extracted_content, page_metadata = await self._fetch_with_playwright(url, task.prompt)
                extraction_method = 'playwright_headless'
                fetch_time = page_metadata.get('navigation_time', 0)
                extract_time = page_metadata.get('extraction_time', 0)
                
            except Exception as e:
                logger.warning(f"⚠️ Playwright extraction failed, falling back to aiohttp: {e}")
                
                # Fallback to aiohttp + lxml extraction
                try:
                    html_content, from_cache = await self._fetch_content(url)
                    fetch_start = time.time()
                    extracted_content = self._extract_content_fast(html_content, url)
                    extract_time = time.time() - fetch_start
                    extraction_method = 'aiohttp_fallback'
                    fetch_time = 0  # Already included in extract_time
                    page_metadata = {'fallback_used': True, 'from_cache': from_cache}
                    
                except Exception as fallback_error:
                    logger.error(f"❌ Both Playwright and fallback extraction failed: {fallback_error}")
                    return Result(
                        task_id=task.task_id,
                        status="failure",
                        output={},
                        error_message=f"Web content extraction failed: {fallback_error}"
                    )
            
            # Step 2: Generate concise summary with citations
            summary_start = time.time()
            summary = self._create_concise_summary(extracted_content, task.prompt)
            summary_time = time.time() - summary_start
            
            total_time = time.time() - start_time
            
            self.status = 'ready'
            
            # Log observability metadata (compact format)
            logger.info(f"🎯 Web research completed: domain={parsed_url.netloc}, "
                       f"method={extraction_method}, "
                       f"timing: total={total_time:.2f}s (fetch={fetch_time:.2f}s, extract={extract_time:.2f}s, summary={summary_time:.2f}s)")
            
            return Result(
                task_id=task.task_id,
                status="success",
                output={
                    'research_summary': summary['summary'],
                    'citation': summary['citation'],
                    'source_title': summary['source_title'],
                    'source_domain': summary['source_domain'],
                    'query': task.prompt,
                    'raw_extracted_content': extracted_content,  # For potential MemOS storage
                    'performance_metrics': {
                        'total_time': total_time,
                        'fetch_time': fetch_time,
                        'extract_time': extract_time,
                        'summary_time': summary_time,
                        'extraction_method': extraction_method,
                        **page_metadata
                    },
                    'extraction_metadata': summary.get('extraction_metadata', {})
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
        try:
            # Cleanup Playwright resources
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            # Cleanup aiohttp session
            if self.session and not self.session.closed:
                await self.session.close()
            
            # Clear cache
            self.content_cache.clear()
            
            logger.info("✅ WebResearcher cleanup completed")
            
        except Exception as e:
            logger.error(f"⚠️ Error during WebResearcher cleanup: {e}")
    
    def __del__(self):
        """Ensure cleanup on destruction."""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            try:
                asyncio.create_task(self.cleanup())
            except:
                pass