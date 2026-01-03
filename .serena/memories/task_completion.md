# Task Completion Checklist

When completing a task, follow these steps:

## Before Committing

1. **Run Tests**
   ```bash
   uv run pytest -v
   ```
   Ensure all tests pass.

2. **Check for Type Errors** (if applicable)
   - Python uses type hints but no strict type checker configured
   - TypeScript in web/ has strict mode

3. **Manual Testing**
   - If changing capture logic: `uv run python main.py` and verify screenshots
   - If changing API: Check `/docs` for endpoint behavior
   - If changing web UI: `cd web && npm run dev` and test in browser

## Code Quality

- Follow existing code patterns in the file
- Add type hints for new functions
- Add docstrings for public functions/classes
- Keep functions focused and small
- Use meaningful variable names

## Testing Guidelines

- Tests are in `tests/` directory
- Test files: `test_*.py`
- Test functions: `test_*`
- Use `@patch` for mocking dependencies
- Test both success and error cases

## No Linting/Formatting Tools Configured

The project does not have ruff, black, or other formatters configured.
Match the existing code style manually.

## Commit Messages

Use conventional commit format:
- `feat: add new feature`
- `fix: resolve bug`
- `refactor: improve code structure`
- `docs: update documentation`
- `test: add tests`
