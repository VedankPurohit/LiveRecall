# Code Style and Conventions

## Attribution
- Never add "Claude Code", "Claude", or any AI name/attribution to commits, PRs, or any other content
- Do not include AI co-author tags in commits
- Do not mention AI assistance in PR descriptions

## Python

### General Style
- Python 3.10+ with type hints
- Double quotes for strings
- 4 spaces for indentation
- Max line length ~100 characters

### Type Hints
```python
from typing import Optional, Callable

def my_function(
    name: str,
    count: int = 0,
    callback: Optional[Callable[[str], None]] = None
) -> bool:
    ...
```

### Docstrings
- Triple double quotes
- Short description on first line
```python
def my_function():
    """Short description of what the function does."""
    ...

def complex_function(arg1: str, arg2: int) -> dict:
    """
    Longer description for complex functions.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value
    """
    ...
```

### Class Structure
```python
class MyService:
    """Service description"""

    def __init__(self):
        self._private_var = None  # Private with underscore prefix

    @property
    def public_prop(self) -> bool:
        """Property description"""
        return self._private_var is not None
```

### Naming Conventions
- `snake_case` for functions, methods, variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- `_leading_underscore` for private attributes

### Global Instances
- Services use global singleton instances at module level:
```python
# Global capture service instance
capture_service = CaptureService()
```

## FastAPI Routes

```python
router = APIRouter(prefix="/recording", tags=["Recording"])

@router.get("", response_model=RecordingStatus)
@router.get("/status", response_model=RecordingStatus)
async def get_status():
    """Get current recording status"""
    return get_recording_status()
```

## TypeScript/React (Web UI)

### General
- TypeScript with strict mode
- Functional components with hooks
- Tailwind CSS for styling

### Naming
- `PascalCase` for components
- `camelCase` for functions and variables
- `kebab-case` for CSS classes

### File Structure
```typescript
// Types at top
interface Props {
  value: string;
}

// Component
export function MyComponent({ value }: Props) {
  // Hooks
  const [state, setState] = useState<string>('');

  // Event handlers
  const handleClick = () => { ... };

  // Render
  return <div>...</div>;
}
```

## Error Handling

### Python
```python
try:
    result = do_something()
except Exception as e:
    print(f"Error: {e}")
    # Handle gracefully, don't crash
```

### API Responses
- Use FastAPI's HTTPException for errors
- Return success/message format for mutations:
```python
return {"success": True, "message": "Operation completed"}
```
