---
inclusion: always
---

# API Design Guidelines

## RESTful API Principles

### HTTP Methods and Usage
- **GET**: Retrieve data, should be idempotent and safe
- **POST**: Create new resources or non-idempotent operations
- **PUT**: Update entire resource, should be idempotent
- **PATCH**: Partial resource updates
- **DELETE**: Remove resources, should be idempotent

### URL Design Patterns
```
# Good: Resource-based URLs
GET    /api/v1/repositories
POST   /api/v1/repositories
GET    /api/v1/repositories/{id}
PUT    /api/v1/repositories/{id}
DELETE /api/v1/repositories/{id}

# Nested resources
GET    /api/v1/repositories/{id}/forks
POST   /api/v1/repositories/{id}/forks/{fork_id}/analyze

# Bad: Action-based URLs
# POST /api/v1/createRepository
# GET  /api/v1/getRepositoryById/{id}
```

### HTTP Status Codes
Use appropriate status codes to communicate response state:

```python
from enum import IntEnum

class HTTPStatus(IntEnum):
    # Success
    OK = 200                    # Successful GET, PUT, PATCH
    CREATED = 201              # Successful POST
    ACCEPTED = 202             # Async operation started
    NO_CONTENT = 204           # Successful DELETE
    
    # Client Errors
    BAD_REQUEST = 400          # Invalid request data
    UNAUTHORIZED = 401         # Authentication required
    FORBIDDEN = 403            # Access denied
    NOT_FOUND = 404            # Resource not found
    METHOD_NOT_ALLOWED = 405   # HTTP method not supported
    CONFLICT = 409             # Resource conflict
    UNPROCESSABLE_ENTITY = 422 # Validation errors
    TOO_MANY_REQUESTS = 429    # Rate limit exceeded
    
    # Server Errors
    INTERNAL_SERVER_ERROR = 500 # Generic server error
    BAD_GATEWAY = 502          # Upstream service error
    SERVICE_UNAVAILABLE = 503   # Service temporarily down
```

## Request and Response Design

### Request Format Standards
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CreateRepositoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    private: bool = False
    tags: List[str] = Field(default_factory=list, max_items=10)

class UpdateRepositoryRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    private: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)
```

### Response Format Standards
```python
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    meta: Optional[dict] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response format"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Example usage
class RepositoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    fork_count: int
    star_count: int

# Success response
def success_response(data: T, message: str = None) -> APIResponse[T]:
    return APIResponse(success=True, data=data, message=message)

# Error response
def error_response(errors: List[str], message: str = None) -> APIResponse[None]:
    return APIResponse(success=False, errors=errors, message=message)
```

### Error Response Format
```python
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    path: str
    request_id: str

# Example error responses
{
    "error": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
        {
            "field": "email",
            "code": "INVALID_FORMAT",
            "message": "Email format is invalid"
        }
    ],
    "timestamp": "2024-01-15T10:30:00Z",
    "path": "/api/v1/users",
    "request_id": "req_123456789"
}
```

## Pagination and Filtering

### Pagination Implementation
```python
from typing import Optional

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
class FilterParams(BaseModel):
    search: Optional[str] = Field(None, max_length=100)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    tags: Optional[List[str]] = None

async def get_repositories(
    pagination: PaginationParams,
    filters: FilterParams
) -> PaginatedResponse[RepositoryResponse]:
    """Get repositories with pagination and filtering"""
    
    # Build query with filters
    query = Repository.select()
    
    if filters.search:
        query = query.where(Repository.name.contains(filters.search))
    if filters.created_after:
        query = query.where(Repository.created_at >= filters.created_after)
    if filters.created_before:
        query = query.where(Repository.created_at <= filters.created_before)
    if filters.tags:
        query = query.where(Repository.tags.contains_any(filters.tags))
    
    # Get total count
    total = await query.count()
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    items = await query.offset(offset).limit(pagination.page_size)
    
    return PaginatedResponse(
        items=[RepositoryResponse.from_orm(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        has_next=offset + pagination.page_size < total,
        has_previous=pagination.page > 1
    )
```

### Query Parameter Standards
```
# Pagination
GET /api/v1/repositories?page=2&page_size=50

# Filtering
GET /api/v1/repositories?search=python&created_after=2024-01-01

# Sorting
GET /api/v1/repositories?sort=created_at&order=desc

# Field selection
GET /api/v1/repositories?fields=id,name,description

# Multiple values
GET /api/v1/repositories?tags=python,web,api
```

## Authentication and Authorization

### Authentication Methods
```python
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return await get_user_by_id(user_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# API Key authentication
async def get_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """Validate API key"""
    if not await is_valid_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key
```

### Authorization Patterns
```python
from enum import Enum
from typing import List

class Permission(Enum):
    READ_REPOSITORIES = "read:repositories"
    WRITE_REPOSITORIES = "write:repositories"
    DELETE_REPOSITORIES = "delete:repositories"
    ADMIN = "admin"

class Role(Enum):
    USER = "user"
    MAINTAINER = "maintainer"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    Role.USER: [Permission.READ_REPOSITORIES],
    Role.MAINTAINER: [Permission.READ_REPOSITORIES, Permission.WRITE_REPOSITORIES],
    Role.ADMIN: [perm for perm in Permission]
}

def require_permission(required_permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
            if required_permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/api/v1/repositories/{repo_id}")
@require_permission(Permission.DELETE_REPOSITORIES)
async def delete_repository(repo_id: int, current_user: User):
    # Implementation here
    pass
```

## API Versioning

### URL-based Versioning
```python
from fastapi import APIRouter

# Version 1 API
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/repositories")
async def get_repositories_v1():
    # V1 implementation
    pass

# Version 2 API with breaking changes
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/repositories")
async def get_repositories_v2():
    # V2 implementation with different response format
    pass

# Include both versions
app.include_router(v1_router)
app.include_router(v2_router)
```

### Header-based Versioning
```python
from fastapi import Header

async def get_repositories(
    api_version: str = Header("1.0", alias="API-Version")
):
    if api_version == "1.0":
        return await get_repositories_v1()
    elif api_version == "2.0":
        return await get_repositories_v2()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {api_version}"
        )
```

## Rate Limiting and Throttling

### Rate Limiting Implementation
```python
import time
from collections import defaultdict
from fastapi import HTTPException, Request

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < window
        ]
        
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True
        return False

rate_limiter = RateLimiter()

def rate_limit(requests_per_minute: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            if not rate_limiter.is_allowed(client_ip, requests_per_minute, 60):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": "60"}
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.get("/api/v1/repositories")
@rate_limit(requests_per_minute=100)
async def get_repositories(request: Request):
    # Implementation here
    pass
```

## API Documentation

### OpenAPI/Swagger Configuration
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Forkscout API",
    description="GitHub repository fork analysis API",
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Endpoint Documentation
```python
from fastapi import Path, Query
from typing import List

@app.get(
    "/api/v1/repositories/{repo_id}/forks",
    response_model=PaginatedResponse[ForkResponse],
    summary="Get repository forks",
    description="Retrieve all forks of a specific repository with optional filtering",
    responses={
        200: {"description": "Successfully retrieved forks"},
        404: {"description": "Repository not found"},
        429: {"description": "Rate limit exceeded"},
    },
    tags=["repositories", "forks"]
)
async def get_repository_forks(
    repo_id: int = Path(..., description="Repository ID", example=123),
    active_only: bool = Query(False, description="Filter for active forks only"),
    min_stars: int = Query(0, description="Minimum star count", ge=0),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user)
) -> PaginatedResponse[ForkResponse]:
    """
    Get all forks of a repository with optional filtering.
    
    This endpoint returns a paginated list of forks for the specified repository.
    You can filter results by activity status and minimum star count.
    """
    # Implementation here
    pass
```

## Testing API Endpoints

### API Test Structure
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_test_jwt_token(user_id=1)
    return {"Authorization": f"Bearer {token}"}

def test_get_repositories_success(client, auth_headers):
    """Test successful repository retrieval"""
    response = client.get("/api/v1/repositories", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "items" in data["data"]
    assert "total" in data["data"]

def test_get_repositories_unauthorized(client):
    """Test unauthorized access"""
    response = client.get("/api/v1/repositories")
    
    assert response.status_code == 401
    assert "authentication" in response.json()["message"].lower()

def test_create_repository_validation_error(client, auth_headers):
    """Test validation error handling"""
    invalid_data = {"name": ""}  # Empty name should fail validation
    
    response = client.post(
        "/api/v1/repositories",
        json=invalid_data,
        headers=auth_headers
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "validation" in data["message"].lower()
    assert len(data["details"]) > 0

def test_rate_limiting(client, auth_headers):
    """Test rate limiting functionality"""
    # Make requests up to the limit
    for _ in range(60):  # Assuming 60 requests per minute limit
        response = client.get("/api/v1/repositories", headers=auth_headers)
        if response.status_code == 429:
            break
    
    # Next request should be rate limited
    response = client.get("/api/v1/repositories", headers=auth_headers)
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
```