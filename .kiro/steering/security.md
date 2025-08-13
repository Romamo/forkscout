---
inclusion: always
---

# Security Guidelines

## Secrets Management

### Environment Variables
- Never commit secrets, API keys, or passwords to version control
- Use environment variables for all sensitive configuration
- Store secrets in `.env` files (ensure they're in `.gitignore`)
- Use different secrets for different environments (dev, staging, prod)

### Secret Storage Best Practices
- Use dedicated secret management services when possible
- Implement proper token rotation policies
- Use least-privilege access principles
- Audit secret access regularly
- Never log or print sensitive information

### Example Secret Handling
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Good: Use environment variables
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable is required")

# Bad: Never hardcode secrets
# API_KEY = "sk-1234567890abcdef"  # DON'T DO THIS
```

## Input Validation and Sanitization

### Validation Principles
- Validate all user inputs at application boundaries
- Use allowlists rather than blocklists when possible
- Implement both client-side and server-side validation
- Sanitize data before processing or storage
- Reject invalid input rather than attempting to fix it

### Common Validation Patterns
```python
from pydantic import BaseModel, validator
import re

class UserInput(BaseModel):
    email: str
    username: str
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError('Username must be 3-20 alphanumeric characters')
        return v
```

### SQL Injection Prevention
- Always use parameterized queries or ORM methods
- Never concatenate user input directly into SQL strings
- Use prepared statements for database operations
- Validate and sanitize all database inputs

```python
# Good: Parameterized query
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# Bad: String concatenation
# cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")  # DON'T DO THIS
```

## API Security

### Authentication and Authorization
- Implement proper authentication for all API endpoints
- Use JWT tokens or similar secure token mechanisms
- Implement role-based access control (RBAC)
- Validate tokens on every request
- Use HTTPS for all API communications

### Rate Limiting
- Implement rate limiting to prevent abuse
- Use different limits for different endpoint types
- Consider user-based and IP-based limiting
- Return appropriate HTTP status codes (429 Too Many Requests)
- Log rate limit violations for monitoring

### API Security Headers
```python
# Security headers to include in API responses
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'"
}
```

## Data Protection

### Encryption
- Encrypt sensitive data at rest and in transit
- Use strong encryption algorithms (AES-256, RSA-2048+)
- Implement proper key management practices
- Never store encryption keys with encrypted data
- Use TLS 1.2+ for all network communications

### Personal Data Handling
- Implement data minimization principles
- Provide data export and deletion capabilities
- Log access to personal data for audit trails
- Implement proper data retention policies
- Consider GDPR and other privacy regulations

### Password Security
```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

## Error Handling and Information Disclosure

### Secure Error Handling
- Never expose sensitive information in error messages
- Log detailed errors internally, return generic messages to users
- Implement proper error logging and monitoring
- Use different error handling for development vs production

### Information Disclosure Prevention
```python
# Good: Generic error message
try:
    user = authenticate_user(username, password)
except AuthenticationError:
    return {"error": "Invalid credentials"}

# Bad: Specific error information
# except UserNotFoundError:
#     return {"error": "User does not exist"}  # DON'T DO THIS
# except InvalidPasswordError:
#     return {"error": "Password is incorrect"}  # DON'T DO THIS
```

## Dependency Security

### Dependency Management
- Regularly update dependencies to latest secure versions
- Use dependency scanning tools to identify vulnerabilities
- Pin dependency versions in production
- Review security advisories for used packages
- Remove unused dependencies

### Security Scanning
```bash
# Use safety to check for known vulnerabilities
uv run safety check

# Use bandit for security linting
uv run bandit -r src/

# Use semgrep for additional security analysis
uv run semgrep --config=auto src/
```

## Logging and Monitoring

### Security Logging
- Log all authentication attempts (success and failure)
- Log access to sensitive resources
- Log security-relevant configuration changes
- Implement log integrity protection
- Never log sensitive data (passwords, tokens, PII)

### Monitoring and Alerting
- Monitor for unusual access patterns
- Set up alerts for security events
- Implement intrusion detection
- Monitor for data exfiltration attempts
- Regular security audit logs review

### Secure Logging Example
```python
import logging
import hashlib

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_user_action(user_id: str, action: str, resource: str):
    """Log user actions without exposing sensitive data"""
    # Hash user_id for privacy
    hashed_user = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    logging.info(f"User {hashed_user} performed {action} on {resource}")
```

## Security Testing

### Security Test Types
- Include security tests in your test suite
- Test input validation and boundary conditions
- Test authentication and authorization flows
- Perform penetration testing on critical features
- Use automated security scanning tools

### Security Test Examples
```python
def test_sql_injection_prevention():
    """Test that SQL injection attempts are blocked"""
    malicious_input = "'; DROP TABLE users; --"
    with pytest.raises(ValidationError):
        validate_user_input(malicious_input)

def test_unauthorized_access():
    """Test that unauthorized requests are rejected"""
    response = client.get("/admin/users")
    assert response.status_code == 401
```