# Security Report

## Known Vulnerabilities and Their Status

This document tracks known security vulnerabilities in the project dependencies and their resolution status.

### Fixed Vulnerabilities

The following vulnerabilities have been addressed in the latest updates:

1. **CVE-2024-6827** (gunicorn) - HTTP Request Smuggling
   - Status: ✅ Fixed by upgrading to gunicorn 23.0.0
   - Previous version: 21.2.0

2. **CVE-2024-47081** (requests) - Credential Leak via .netrc
   - Status: ✅ Fixed by upgrading to requests 2.32.5
   - Previous version: 2.32.3

3. **CVE-2024-53981, CVE-2026-24486** (python-multipart)
   - Status: ✅ Fixed by upgrading to python-multipart 0.0.22
   - Previous version: 0.0.9

4. **PYSEC-2024-232, PYSEC-2024-233** (python-jose)
   - Status: ✅ Fixed by upgrading to python-jose[cryptography] 3.4.0
   - Previous version: 3.3.0

5. **Multiple vulnerabilities** (PyMuPDF)
   - Status: ✅ Fixed by upgrading to PyMuPDF 1.26.0
   - Previous version: 1.24.9

6. **Python 3.12 Compatibility Issues**
   - Status: ✅ Fixed by upgrading:
     - faiss-cpu 1.7.4 → 1.8.0
     - dowhy 0.11.1 → 0.13

### Known Vulnerabilities That Cannot Be Fixed

The following vulnerabilities cannot be fixed due to dependency constraints:

#### 1. CVE-2024-23342 (ecdsa)
- **Status**: ⚠️ Cannot be fixed (no patch available)
- **Reason**: The `ecdsa` package maintainers have stated that constant-time side-channel resilience is not in scope for the pure Python implementation. No fix is planned.
- **Mitigation**: Using `python-jose[cryptography]` ensures that the `cryptography` library (which uses secure constant-time implementations) is used instead of `ecdsa` for actual cryptographic operations.
- **Source**: Indirect dependency via `python-jose`

#### 2. Multiple CVEs in transformers 4.43.4
- **Status**: ⚠️ Cannot be upgraded
- **Affected CVEs**: 
  - PYSEC-2024-227, PYSEC-2024-228, PYSEC-2024-229, PYSEC-2025-40
  - CVE-2024-12720, CVE-2025-1194, CVE-2025-3263, CVE-2025-3264
  - CVE-2025-3777, CVE-2025-3933, CVE-2025-5197, CVE-2025-6638
  - CVE-2025-6051, CVE-2025-6921
- **Reason**: `camel-tools 1.5.7` requires `transformers<4.44.0`. Upgrading transformers would require updating or replacing camel-tools, which is a core dependency for Arabic NLP functionality.
- **Fix version needed**: 4.53.0
- **Current version**: 4.43.4
- **Recommended action**: Monitor `camel-tools` for updates that support newer transformers versions

#### 3. Multiple CVEs in torch 2.4.1
- **Status**: ⚠️ Cannot be upgraded  
- **Affected CVEs**:
  - PYSEC-2024-259, PYSEC-2025-41
  - CVE-2025-2953, CVE-2025-3730
- **Reason**: PyTorch is a large, complex dependency with potential compatibility issues across the ML stack. Upgrading would require extensive testing of model loading, training, and inference pipelines.
- **Fix version needed**: 2.8.0
- **Current version**: 2.4.1
- **Recommended action**: Schedule upgrade in a separate maintenance window with comprehensive testing

#### 4. CVE-2025-54121, CVE-2025-62727 (starlette)
- **Status**: ⚠️ Transitive dependency (managed by FastAPI)
- **Reason**: Starlette is a dependency of FastAPI. The version is constrained by FastAPI's compatibility requirements.
- **Fix version needed**: 0.49.1
- **Current version**: 0.46.2 (via fastapi 0.115.14)
- **Recommended action**: Monitor FastAPI updates for versions that support safer Starlette versions

#### 5. PYSEC-2022-252 (deep-translator)
- **Status**: ✅ False positive
- **Reason**: This vulnerability only affected version 1.8.5 (a compromised release in August 2022). Current version 1.11.4 is safe.
- **Current version**: 1.11.4

## Security Update Policy

1. All dependencies should be regularly reviewed for security updates
2. Critical and high-severity vulnerabilities should be addressed within 30 days
3. When dependencies cannot be upgraded due to compatibility constraints, document the reasons and monitor for future compatibility updates
4. Use `pip-audit` regularly to scan for new vulnerabilities

## Running Security Audits

To check for vulnerabilities in the current environment:

```bash
pip install pip-audit
pip-audit
```

## Last Updated

This report was last updated on: 2026-01-30
