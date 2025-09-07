#!/usr/bin/env python3
"""
Demonstration of rate limiting and error handling in the GitHub client.

This script shows how the enhanced GitHub client handles various error conditions
and implements retry logic with exponential backoff.
"""

import asyncio
import logging
from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.rate_limiter import RateLimitHandler, CircuitBreaker

# Configure logging to see the retry behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def demonstrate_rate_limiting():
    """Demonstrate rate limiting and error handling features."""
    
    # Create configuration (you would normally load this from a file or environment)
    config = GitHubConfig(
        token="your-github-token-here",  # Replace with actual token
        base_url="https://api.github.com",
        timeout_seconds=30,
    )
    
    # Create custom rate limiter with specific settings
    rate_limiter = RateLimitHandler(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_factor=2.0,
        jitter=True,
    )
    
    # Create circuit breaker for resilience
    circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        timeout=60.0,
    )
    
    # Create GitHub client with enhanced error handling
    async with GitHubClient(
        config=config,
        rate_limit_handler=rate_limiter,
        circuit_breaker=circuit_breaker,
    ) as client:
        
        print("=== GitHub Client Rate Limiting Demo ===\n")
        
        # 1. Check current rate limit status
        print("1. Checking rate limit status...")
        try:
            rate_status = await client.check_rate_limit()
            print(f"   Rate limit: {rate_status['remaining']}/{rate_status['limit']}")
            print(f"   Reset time: {rate_status['reset']}")
        except Exception as e:
            print(f"   Error checking rate limit: {e}")
        
        print()
        
        # 2. Check circuit breaker status
        print("2. Circuit breaker status:")
        cb_status = client.get_circuit_breaker_status()
        print(f"   State: {cb_status['state']}")
        print(f"   Failure count: {cb_status['failure_count']}")
        print(f"   Threshold: {cb_status['failure_threshold']}")
        
        print()
        
        # 3. Demonstrate repository fetching with error handling
        print("3. Fetching repository information...")
        try:
            # This will automatically retry on rate limits, network errors, etc.
            repo = await client.get_repository("octocat", "Hello-World")
            print(f"   Repository: {repo.full_name}")
            print(f"   Stars: {repo.stars}")
            print(f"   Language: {repo.language}")
        except Exception as e:
            print(f"   Error fetching repository: {e}")
        
        print()
        
        # 4. Demonstrate fork listing with pagination
        print("4. Fetching repository forks...")
        try:
            forks = await client.get_repository_forks("octocat", "Hello-World", per_page=5)
            print(f"   Found {len(forks)} forks (first page)")
            for fork in forks[:3]:  # Show first 3
                print(f"   - {fork.full_name} ({fork.stars} stars)")
        except Exception as e:
            print(f"   Error fetching forks: {e}")
        
        print()
        
        # 5. Show final circuit breaker status
        print("5. Final circuit breaker status:")
        final_status = client.get_circuit_breaker_status()
        print(f"   State: {final_status['state']}")
        print(f"   Failure count: {final_status['failure_count']}")
        
        print("\n=== Demo Complete ===")


async def demonstrate_error_scenarios():
    """Demonstrate how different error types are handled."""
    
    config = GitHubConfig(
        token="invalid-token",  # This will cause authentication errors
        base_url="https://api.github.com",
        timeout_seconds=5,
    )
    
    client = GitHubClient(config=config)
    
    print("\n=== Error Handling Demo ===\n")
    
    # Test authentication error (should not retry)
    print("1. Testing authentication error (no retry)...")
    try:
        await client.get_repository("octocat", "Hello-World")
    except Exception as e:
        print(f"   Expected error: {type(e).__name__}: {e}")
    
    print()
    
    # Test not found error (should not retry)
    print("2. Testing not found error (no retry)...")
    try:
        # Use a valid token but non-existent repo
        config.token = "ghp_valid_token_format_but_fake_1234567890abcdef"
        client = GitHubClient(config=config)
        await client.get_repository("nonexistent", "nonexistent-repo")
    except Exception as e:
        print(f"   Expected error: {type(e).__name__}: {e}")
    
    await client.close()
    
    print("\n=== Error Demo Complete ===")


if __name__ == "__main__":
    print("GitHub Client Rate Limiting and Error Handling Demo")
    print("=" * 50)
    
    # Note: This demo requires a valid GitHub token to work properly
    print("\nNOTE: To run this demo with real API calls, you need to:")
    print("1. Set a valid GitHub token in the config")
    print("2. Ensure you have internet connectivity")
    print("3. Be aware that this will use your GitHub API rate limit")
    
    print("\nRunning demo with mock scenarios...")
    
    # Run the demonstrations
    asyncio.run(demonstrate_error_scenarios())
    
    print("\nTo run the full demo with real API calls:")
    print("python examples/rate_limiting_demo.py --real-api")