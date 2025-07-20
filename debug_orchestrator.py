"""
Debug orchestrator prompt classification
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import ProjectManager


async def debug_prompt_classification():
    """Debug how prompts are classified by the orchestrator."""
    
    pm = ProjectManager()
    
    test_prompts = [
        "Fix the bug in the calculate_total function by adding null checks",
        "Edit the main function to add error handling", 
        "Modify the UserService class to include validation",
        "Update the process_data method in the analytics module",
        "Fix bug in function calculate_area",
        "Change variable name in the helper function"
    ]
    
    print("🔍 Debug Prompt Classification")
    print("=" * 50)
    
    for prompt in test_prompts:
        print(f"\n📝 Prompt: '{prompt}'")
        
        prompt_lower = prompt.lower()
        
        # Check each classification condition
        
        # Web research
        web_keywords = ['scrape', 'web', 'website', 'url', 'fetch', 'extract from', 'get from', 'ricerca web',
                       'scraping', 'website content', 'page content', 'estrai da', 'ottieni da']
        has_web = any(keyword in prompt_lower for keyword in web_keywords)
        print(f"  Web research: {has_web}")
        
        # Codebase knowledge
        codebase_keywords = ['trova', 'cerca', 'dove', 'come funziona', 'che cosa fa', 'explain', 'find', 'search', 
                           'where', 'how does', 'what does', 'show me', 'mostrami', 'function', 'funzione',
                           'class', 'classe', 'method', 'metodo', 'file', 'directory', 'cartella']
        has_codebase = any(keyword in prompt_lower for keyword in codebase_keywords)
        print(f"  Codebase query: {has_codebase}")
        
        # Code generation
        generation_keywords = ['genera', 'crea', 'scrivi', 'implementa', 'develop', 'build', 'create']
        has_generation = any(keyword in prompt_lower for keyword in generation_keywords)
        print(f"  Code generation: {has_generation}")
        
        # Code editing
        editing_keywords = ['modifica', 'edit', 'cambia', 'change', 'fix', 'correggi', 'aggiorna', 'update', 
                          'refactor', 'rifattorizza', 'migliora', 'improve', 'applica', 'apply', 'bug']
        has_editing = any(keyword in prompt_lower for keyword in editing_keywords)
        print(f"  Code editing: {has_editing}")
        
        # Code editing with context
        context_keywords = ['file', 'function', 'class', 'method', 'nel progetto', 'in the project', 'the ']
        has_context = any(keyword in prompt_lower for keyword in context_keywords)
        print(f"  Has context: {has_context}")
        
        # Generate plan
        plan = await pm._decompose_prompt(prompt)
        print(f"  Generated plan: {len(plan)} steps")
        
        for i, step in enumerate(plan, 1):
            print(f"    Step {i}: {step['agent_role']}")
        
        has_code_editor = any(step['agent_role'] == 'code_editor' for step in plan)
        print(f"  Code editor in plan: {'✅' if has_code_editor else '❌'}")


if __name__ == "__main__":
    asyncio.run(debug_prompt_classification())