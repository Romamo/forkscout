---
inclusion: always
---

# Environment Variable Management

## Use .env Files for Configuration

Always use `.env` files for managing environment variables in this project:

- Store sensitive configuration (API keys, database URLs, secrets) in `.env` files
- Use `.env.example` to document required environment variables without exposing values
- Load environment variables using `python-dotenv` or similar libraries
- Never commit `.env` files to version control (ensure they're in `.gitignore`)

## Environment Variable Conventions

- Use UPPERCASE_WITH_UNDERSCORES for variable names
- Prefix project-specific variables with a consistent identifier
- Use descriptive names that clearly indicate purpose
- Provide default values in code when appropriate

## Example Usage

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///default.db')
API_KEY = os.getenv('API_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
```

## File Structure

- `.env` - Local development environment variables (not committed)
- `.env.example` - Template showing required variables (committed)
- `.env.test` - Test environment variables (if needed)