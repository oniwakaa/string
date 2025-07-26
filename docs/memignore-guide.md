# .memignore File Guide

The `.memignore` file provides complete user control over which files are loaded into the AI coding assistant's memory. This system replaces complex universal filtering with simple, extensible user control.

## Quick Start

1. **Create a .memignore file** in your project root:
   ```bash
   touch .memignore
   ```

2. **Add exclusion patterns** (one per line):
   ```
   node_modules/
   __pycache__/
   *.log
   build/
   ```

3. **Reload your codebase** and the AI will only load files not matching these patterns.

## Pattern Syntax

The `.memignore` file uses **gitignore-style patterns**:

### Basic Patterns
- `filename.txt` - exclude specific file
- `*.log` - exclude all .log files
- `directory/` - exclude entire directory and all contents
- `path/to/file.js` - exclude specific file at specific path

### Wildcards
- `*` - matches any characters (except /)
- `**` - matches any characters including /
- `?` - matches any single character
- `[abc]` - matches any character in brackets

### Advanced Patterns
- `**/temp` - exclude any 'temp' directory at any level
- `build/**` - exclude everything inside build directory
- `!important.txt` - include file even if excluded by earlier pattern
- `# comment` - comments start with #

## Common Use Cases

### Python Projects
```
# Python
__pycache__/
*.pyc
venv/
.venv/
.pytest_cache/
.coverage
htmlcov/
```

### JavaScript/Node.js Projects
```
# Node.js
node_modules/
npm-debug.log
yarn-error.log
.next/
.nuxt/
dist/
build/
```

### Multiple Languages
```
# Build outputs
build/
dist/
out/
target/
bin/

# IDE files
.vscode/
.idea/
*.swp

# Logs
*.log
logs/
```

### Large Files/Data
```
# Large binary files
*.zip
*.pdf
*.png
*.mp4
data/
models/
*.db
```

## Best Practices

### 1. Start Simple
Begin with basic patterns and add more as needed:
```
.git/
node_modules/
__pycache__/
*.log
```

### 2. Be Specific
Prefer specific patterns over broad ones:
```
# Good - specific
build/
dist/
node_modules/

# Avoid - too broad
temp*
```

### 3. Test and Iterate
- Load your codebase and check the results
- Review the filtering stats in the response
- Adjust patterns based on what was included/excluded

### 4. Document Your Patterns
Use comments to explain why patterns exist:
```
# Exclude build outputs
build/
dist/

# Large data files that don't need AI analysis
data/large-datasets/
models/pretrained/
```

## Advanced Usage

### Inclusion Overrides
Use `!` to include files that would otherwise be excluded:
```
# Exclude all txt files
*.txt

# But include the important readme
!README.txt
!docs/important.txt
```

### Conditional Patterns
You can use the API to add additional patterns programmatically:
```python
# In your code
additional_patterns = ['test/' if skip_tests else '']
result = service.load_codebase(
    directory_path="./",
    additional_patterns=additional_patterns
)
```

### Custom .memignore Location
Specify a custom .memignore file location:
```python
result = service.load_codebase(
    directory_path="./",
    custom_memignore_path="/path/to/custom.memignore"
)
```

## Troubleshooting

### No Files Loaded
If no files are loaded:
1. Check that patterns aren't too restrictive
2. Look at the `exclusion_breakdown` in the response
3. Comment out patterns with `#` to test

```
# Temporarily disable to test
# *.py
# *.js
```

### Too Many Files Loaded
If too many files are loaded:
1. Add more specific exclusion patterns
2. Use directory exclusions for broad filtering
3. Check for missing trailing slashes on directories

```
# Add these to reduce file count
test/
examples/
docs/
vendor/
```

### Performance Issues
For large codebases:
1. Exclude unnecessary directories early in .memignore
2. Use broad patterns for file types you don't need
3. Monitor the filtering stats and total size

## API Response Information

The new load_codebase API provides detailed filtering information:

```json
{
  "status": "success",
  "filtering_method": ".memignore-based",
  "memignore_exists": true,
  "files_loaded": 245,
  "files_failed": 3,
  "inclusion_rate": 0.15,
  "filtering_stats": {
    "total_files_found": 1632,
    "total_files_included": 248,
    "total_files_excluded": 1384,
    "exclusion_breakdown": {
      "memignore_pattern:node_modules/": 892,
      "memignore_pattern:__pycache__/": 156,
      "memignore_pattern:*.log": 45
    }
  }
}
```

Use this information to:
- Understand what was excluded and why
- Optimize your .memignore patterns
- Monitor performance impact

## Migration from Universal Filtering

If you're migrating from the old system:

1. **Remove old parameters**: `file_extensions` and `exclude_dirs` are no longer used
2. **Create .memignore**: Add the exclusions you need
3. **Test thoroughly**: The new system is more permissive by default
4. **Use provided stats**: Monitor what gets included/excluded

The new system provides:
- ✅ Complete user control
- ✅ Project-specific customization  
- ✅ Better performance on large codebases
- ✅ Clear feedback on filtering decisions
- ✅ Simple, familiar syntax

## Examples by Project Type

### Machine Learning Project
```
# ML Project .memignore
data/raw/
data/processed/
models/checkpoints/
*.h5
*.pkl
*.joblib
__pycache__/
.ipynb_checkpoints/
wandb/
mlruns/
```

### Web Application
```
# Web App .memignore
node_modules/
build/
dist/
.next/
coverage/
*.log
.env.local
.DS_Store
public/uploads/
```

### Research/Academic Project
```
# Research .memignore
data/
papers/
*.pdf
*.docx
figures/
plots/
__pycache__/
.venv/
results/large-outputs/
```

Remember: The goal is to include only the source code and configuration files that the AI needs to understand and help with your project!