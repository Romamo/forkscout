---
inclusion: always
---

# Code Organization and Structure Guidelines

## Project Structure Conventions

Follow a clean, modular architecture that separates concerns and promotes maintainability:

```
src/
├── models/          # Data models and domain entities
├── services/        # Business logic and service layer
├── repositories/    # Data access layer
├── controllers/     # API endpoints and request handlers
├── utils/           # Utility functions and helpers
├── config/          # Configuration management
└── exceptions/      # Custom exception classes

tests/
├── unit/           # Unit tests mirroring src structure
├── integration/    # Integration tests
└── fixtures/       # Test data and fixtures
```

## File Organization Rules

### Class Separation
- Each major class should be in its own file
- File names should match the primary class name in snake_case
- Group related classes in the same module only if they're tightly coupled

### Module Naming
- Use descriptive, lowercase module names with underscores
- Avoid generic names like `utils.py` - be specific (`date_utils.py`, `string_helpers.py`)
- Keep module names short but meaningful

### Import Organization
- Standard library imports first
- Third-party imports second
- Local application imports last
- Use absolute imports for clarity
- Group imports logically and separate with blank lines

## Architecture Patterns

### Dependency Injection
- Pass dependencies as constructor parameters
- Use dependency injection for testability
- Avoid global state and singletons where possible

### Layer Separation
- **Models**: Pure data structures with minimal logic
- **Services**: Business logic and orchestration
- **Repositories**: Data access abstraction
- **Controllers**: Request/response handling only

### Interface Design
- Define clear interfaces between layers
- Use abstract base classes for contracts
- Keep interfaces focused and cohesive

## Code Organization Best Practices

### Single Responsibility
- Each class should have one reason to change
- Functions should do one thing well
- Modules should have a clear, focused purpose

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: prefix with single underscore `_private_method`

### File Size Guidelines
- Keep files under 300 lines when possible
- Split large classes into smaller, focused components
- Extract common functionality into utility modules

## Example Structure

```python
# models/user.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    username: str
    email: str
    is_active: bool = True

# services/user_service.py
from models.user import User
from repositories.user_repository import UserRepository

class UserService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
    
    def create_user(self, username: str, email: str) -> User:
        # Business logic here
        pass
```