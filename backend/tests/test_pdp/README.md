# PDP Test Suite

This directory contains comprehensive tests for the Policy Decision Point (PDP) system.

## Overview

The test suite includes **158 test functions** across 7 test files, covering all components of the PDP system:

## Test Files

### 1. `test_policy_engine.py` (12 tests)
Tests for the core PolicyEngine class that orchestrates policy evaluation.

**Key Test Areas:**
- Policy evaluation with allow/deny decisions
- Rate limit enforcement
- Policy priority and chain evaluation
- Role-based and project-based access control
- Content scanning integration
- Audit trail logging

**Example Tests:**
- `test_evaluate_allow` - User with permission should allow
- `test_evaluate_deny_no_permission` - User without permission should deny
- `test_evaluate_deny_rate_limit` - Exceeded rate limit should deny
- `test_policy_priority` - Higher priority policy should override
- `test_chain_evaluation` - Multiple policies evaluated in order

### 2. `test_rules.py` (21 tests)
Tests for individual policy rule classes.

**Key Test Areas:**
- Role-based access control (admin, director, engineer, viewer)
- Project access rules via ACL
- Data classification and clearance levels
- Time-based access (business hours)
- Content prohibition (SSN, SQL injection, XSS, command injection)
- Rate limiting
- Geofencing (IP-based restrictions)

**Example Tests:**
- `test_role_based_rule_admin` - Admin has all permissions
- `test_role_based_rule_viewer` - Viewer has limited permissions
- `test_project_access_rule` - Check ACL-based project access
- `test_time_based_rule_business_hours` - Enforce business hours
- `test_content_prohibition_ssn` - Detect SSN patterns

### 3. `test_acl_manager.py` (21 tests)
Tests for the Access Control List manager.

**Key Test Areas:**
- Granting and revoking access
- Permission checking
- User project listings
- Access expiration
- Role-based permissions mapping
- Admin global access

**Example Tests:**
- `test_grant_access` - Grant user access to project
- `test_revoke_access` - Revoke user access
- `test_check_permission_allowed` - Check if permission is allowed
- `test_check_permission_denied` - Check if permission is denied
- `test_expired_access` - Handle expired access properly

### 4. `test_rate_limiter.py` (17 tests)
Tests for the rate limiting system using sliding window algorithm.

**Key Test Areas:**
- Rate limit checking and enforcement
- Window reset after expiration
- Per-endpoint and per-user limits
- Counter incrementing
- Cleanup of expired records

**Example Tests:**
- `test_under_limit` - Requests under limit are allowed
- `test_at_limit` - Requests at limit are blocked
- `test_window_reset` - Rate limit resets after window expires
- `test_different_endpoints` - Different endpoints have separate limits
- `test_increment` - Counter increments correctly

### 5. `test_content_scanner.py` (36 tests)
Tests for the content security scanner.

**Key Test Areas:**
- PII detection (SSN, credit cards, emails, API keys)
- SQL injection detection
- XSS (Cross-Site Scripting) detection
- Command injection detection
- Content sanitization
- Severity level assignment
- Multiple violation detection

**Example Tests:**
- `test_scan_safe_content` - Safe content passes
- `test_detect_ssn` - Detect Social Security Numbers
- `test_detect_sql_injection` - Detect SQL injection patterns
- `test_detect_xss` - Detect XSS patterns
- `test_detect_command_injection` - Detect command injection
- `test_sanitize_removes_scripts` - Sanitization removes dangerous content

### 6. `test_api.py` (24 tests)
Tests for PDP API endpoints using FastAPI TestClient.

**Key Test Areas:**
- Policy evaluation endpoint
- Access grant/revoke endpoints
- User permissions retrieval
- Rate limit status checking
- Content scanning API
- Audit trail querying
- Policy CRUD operations

**Example Tests:**
- `test_evaluate_endpoint` - Test policy evaluation API
- `test_grant_access_endpoint` - Test granting access via API
- `test_revoke_access_endpoint` - Test revoking access via API
- `test_permissions_endpoint` - Test getting user permissions
- `test_policies_crud_endpoints` - Test create/update/delete policies

### 7. `test_middleware.py` (27 tests)
Tests for PDPMiddleware integration with FastAPI.

**Key Test Areas:**
- Public endpoint bypass
- Rate limit enforcement in middleware
- Access denial (403 responses)
- Rate limit exceeded (429 responses)
- Request context extraction (user_id, IP, user-agent)
- Decision logging
- Error handling

**Example Tests:**
- `test_middleware_allows_public_endpoints` - Public endpoints bypass PDP
- `test_middleware_checks_rate_limit` - Middleware enforces rate limits
- `test_middleware_blocks_forbidden` - Middleware blocks unauthorized access
- `test_middleware_logs_decision` - All decisions are logged
- `test_middleware_passes_allowed` - Allowed requests pass through

## Running Tests

### Prerequisites
```bash
# Install dependencies
cd backend
pip install -r requirements.txt
```

### Run All Tests
```bash
# Run all PDP tests
pytest backend/tests/test_pdp/ -v

# Run with coverage
pytest backend/tests/test_pdp/ --cov=backend.backend.pdp --cov-report=html
```

### Run Specific Test Files
```bash
# Test policy engine
pytest backend/tests/test_pdp/test_policy_engine.py -v

# Test rules
pytest backend/tests/test_pdp/test_rules.py -v

# Test ACL manager
pytest backend/tests/test_pdp/test_acl_manager.py -v

# Test rate limiter
pytest backend/tests/test_pdp/test_rate_limiter.py -v

# Test content scanner
pytest backend/tests/test_pdp/test_content_scanner.py -v

# Test API
pytest backend/tests/test_pdp/test_api.py -v

# Test middleware
pytest backend/tests/test_pdp/test_middleware.py -v
```

### Run Specific Tests
```bash
# Run a single test
pytest backend/tests/test_pdp/test_policy_engine.py::test_evaluate_allow -v

# Run tests matching a pattern
pytest backend/tests/test_pdp/ -k "rate_limit" -v
```

## Test Structure

All tests follow a consistent pattern:

1. **Fixtures**: Each test file has pytest fixtures that set up:
   - In-memory SQLite database
   - Test users with different roles
   - Test projects
   - ACL entries as needed

2. **Setup/Teardown**: Fixtures handle database creation and cleanup automatically

3. **Isolation**: Each test uses in-memory database for complete isolation

4. **Assertions**: Tests use clear assertions with descriptive messages

5. **Docstrings**: All test functions include docstrings describing what they test

## Test Coverage

The test suite covers:

- ✅ **Policy Engine**: Complete evaluation pipeline
- ✅ **Rules**: All rule types (RBAC, ACL, temporal, content, rate limit, geofence)
- ✅ **ACL Manager**: Permission management and access control
- ✅ **Rate Limiter**: Sliding window algorithm and limits
- ✅ **Content Scanner**: Security pattern detection and sanitization
- ✅ **API Endpoints**: All PDP REST API operations
- ✅ **Middleware**: Request interception and policy enforcement

## Database

All tests use in-memory SQLite databases created via:
```python
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
```

This ensures:
- Fast test execution
- Complete isolation between tests
- No need for database cleanup
- No external dependencies

## Contributing

When adding new tests:

1. Follow the existing pattern with fixtures
2. Use descriptive test function names starting with `test_`
3. Add docstrings to all test functions
4. Use in-memory SQLite for database tests
5. Group related tests in the same file
6. Ensure tests are independent and can run in any order

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run PDP Tests
  run: |
    cd backend
    pytest tests/test_pdp/ -v --cov=backend.backend.pdp
```

## Troubleshooting

### Import Errors
If you see import errors, ensure you're running from the correct directory:
```bash
cd /path/to/diriyah-ai-demo
pytest backend/tests/test_pdp/
```

### Database Errors
If you see database errors, ensure SQLAlchemy models are properly defined in `backend.backend.models` and `backend.backend.pdp.models`.

### Missing Dependencies
Install all required dependencies:
```bash
pip install -r backend/requirements.txt
```

## Summary

This comprehensive test suite provides **158 tests** covering all aspects of the PDP system, ensuring:
- Security policies are correctly enforced
- Rate limiting works as expected
- Content scanning detects threats
- Access control is properly managed
- API endpoints function correctly
- Middleware integrates seamlessly

All tests use modern pytest features including fixtures, parameterization (where applicable), and clear assertions for maintainability.
