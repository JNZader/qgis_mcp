# Security Policy

QGIS MCP Server implements multiple security layers to protect your QGIS instance and data.

---

## 🔒 Security Features

### 1. Authentication

**All connections require authentication**

- 32-byte secure random tokens generated on server start
- Token-based authentication for every request
- Tokens stored securely (system keyring or encrypted file)
- No default/hardcoded credentials

**Best practices:**
- ✅ Never disable authentication (`require_auth=True` always)
- ✅ Rotate tokens regularly (monthly recommended)
- ✅ Don't commit tokens to version control
- ✅ Use environment variables or secure storage

### 2. Network Security

**Localhost-only binding (enforced)**

- Server only listens on `127.0.0.1` (localhost)
- Cannot be accessed from external networks
- Prevents unauthorized remote access

**For remote access:**
- ✅ Use SSH tunneling
- ❌ Never expose to public internet
- ❌ Don't bind to `0.0.0.0`

### 3. TLS/SSL Encryption

**Optional encrypted communication**

- TLS 1.2+ only (no older protocols)
- Auto-generated self-signed certificates
- Secure cipher suites only
- Certificate auto-renewal

**Enable with:**
```python
server = start_optimized_server(use_tls=True)
client = connect(use_tls=True, verify_cert=False)  # Self-signed cert
```

### 4. Code Sandboxing

**Restricted code execution environment**

When using `execute_code()`, only safe operations are allowed:

✅ **Allowed:**
- QGIS core/GUI modules (`qgis.core`, `qgis.gui`)
- PyQt5 Qt modules (`PyQt5.QtCore`, `PyQt5.QtGui`)
- Math and basic Python operations
- List/dict/set operations

❌ **Blocked:**
- File system access (`open()`, `os`, `pathlib`)
- Network operations (`urllib`, `requests`, `socket`)
- System commands (`subprocess`, `os.system`)
- Dynamic imports (`__import__`, `importlib`)
- Dangerous functions (`eval`, `exec`, `compile`)

### 5. Path Validation

**Comprehensive path security**

All file paths are validated through multiple layers:

1. **Real path resolution** - Resolves symlinks
2. **Symlink detection** - Prevents symlink attacks
3. **Unicode normalization** - Prevents Unicode tricks
4. **Null byte check** - Prevents null byte injection
5. **Traversal sequences** - Blocks `../`, `..\\`, etc.
6. **Path length limits** - Prevents buffer overflows
7. **Whitelist validation** - Only allowed directories
8. **Permission checks** - Verifies read/write access

### 6. Rate Limiting

**Tiered rate limits to prevent abuse**

Four tiers of rate limiting:

| Tier | Operations | Limit |
|------|-----------|-------|
| Authentication | Token validation | 5 req / 5 min |
| Expensive | Processing, rendering | 10 req / min |
| Normal | Layer operations | 60 req / min |
| Cheap | Ping, info | 300 req / min |

**Exponential backoff:** Repeated violations increase delay (2^n seconds, max 60s)

### 7. Input Validation

**All inputs validated with JSON Schema**

- Message structure validation
- Type checking (string, number, array, object)
- Range validation (min/max lengths)
- Required fields enforcement
- Size limits (10MB message limit)

---

## ⚠️ Security Warnings

### CRITICAL: Localhost Only

```
⚠️  NEVER EXPOSE THE SERVER TO PUBLIC INTERNET
```

**Why?**
- Even with authentication, public exposure increases attack surface
- Potential for DoS attacks
- Risk of credential theft
- Network-level vulnerabilities

**For remote access, use SSH tunneling:**

```bash
# On your local machine
ssh -L 9876:localhost:9876 user@remote-server

# Now connect to localhost:9876 (tunneled)
```

### IMPORTANT: Authentication Required

```
⚠️  NEVER DISABLE AUTHENTICATION
```

**Bad:**
```python
server = start_optimized_server(require_auth=False)  # ❌ DON'T DO THIS!
```

**Good:**
```python
server = start_optimized_server(require_auth=True)  # ✅ ALWAYS
```

### WARNING: Code Execution

```
⚠️  ONLY EXECUTE TRUSTED CODE
```

The `execute_code()` method is sandboxed but should only run trusted code:
- ✅ Your own scripts
- ✅ Reviewed third-party code
- ❌ User-provided code
- ❌ Untrusted sources

---

## 🛡️ Best Practices

### 1. Secure Token Management

**Store tokens securely:**

```bash
# ✅ GOOD - Environment variable
export QGIS_MCP_TOKEN="$(cat ~/.qgis_mcp/token)"

# ✅ GOOD - System keyring (automatic)
# Tokens stored in Windows Credential Manager, macOS Keychain, etc.

# ❌ BAD - Hardcoded in scripts
TOKEN = "my-secret-token-123"  # Don't commit this!

# ❌ BAD - Plain text config file
echo "token: my-secret" > config.txt  # Insecure!
```

**Rotate tokens regularly:**

```python
# Monthly rotation recommended
server.stop()
server = start_optimized_server(require_auth=True)  # New token generated
```

### 2. Use TLS/SSL in Production

```python
# Development: TLS optional
server = start_optimized_server(use_tls=False)

# Production: TLS required
server = start_optimized_server(use_tls=True)
```

### 3. Monitor Access

```python
# Regular monitoring
with connect(port=9876) as client:
    stats = client.get_performance_stats()

    if stats['total_requests'] > THRESHOLD:
        send_alert("High request volume detected")

    if stats['failed_auth_attempts'] > 10:
        send_alert("Multiple failed auth attempts")
```

### 4. Limit Permissions

Run QGIS with minimum required permissions:

- ✅ Standard user account (not admin/root)
- ✅ Read-only access to data when possible
- ✅ Separate service account for production
- ❌ Never run as administrator/root

### 5. Network Isolation

**Development:**
```python
# Localhost only (automatic)
server = start_optimized_server()  # Binds to 127.0.0.1
```

**Production (remote access):**
```bash
# SSH tunnel
ssh -L 9876:localhost:9876 user@server

# Or VPN
# Connect via VPN, then localhost
```

### 6. Audit Logging

Enable logging for security events:

```python
import logging

logging.basicConfig(
    filename='/var/log/qgis_mcp.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Server automatically logs:
# - Authentication attempts (success/failure)
# - Rate limit violations
# - Suspicious activity
# - Error conditions
```

### 7. Input Sanitization

Even though validation is automatic, sanitize user inputs in your application:

```python
def safe_layer_name(name: str) -> str:
    """Sanitize layer name"""
    # Remove special characters
    import re
    return re.sub(r'[^\w\s-]', '', name)[:100]

# Use it
with connect(port=9876) as client:
    client.add_vector_layer(
        path="/data/file.shp",
        name=safe_layer_name(user_input)
    )
```

---

## 🚨 Reporting Security Issues

**Found a security vulnerability?**

**DO NOT** create a public GitHub issue!

**Instead:**
1. Email: security@your-domain.com
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

3. We will:
   - Acknowledge within 48 hours
   - Investigate and patch
   - Credit you in release notes (if desired)

---

## 📋 Security Checklist

Before deploying to production:

### Server Configuration

- [ ] Authentication enabled (`require_auth=True`)
- [ ] TLS/SSL enabled (`use_tls=True`)
- [ ] Localhost-only binding (automatic)
- [ ] Strong token generated (32+ bytes)
- [ ] Token stored securely (keyring/encrypted)
- [ ] Logs enabled and monitored
- [ ] Rate limiting enabled (automatic)

### Network Security

- [ ] Firewall configured (block external access to port)
- [ ] SSH tunnel configured for remote access
- [ ] VPN configured (if applicable)
- [ ] No port forwarding to public internet

### Access Control

- [ ] Tokens rotated regularly (monthly)
- [ ] Tokens not in version control
- [ ] Tokens not in logs/debug output
- [ ] Service runs as non-privileged user
- [ ] File permissions restricted (0600 for token files)

### Monitoring

- [ ] Logging enabled
- [ ] Log rotation configured
- [ ] Alerts configured for:
  - [ ] Failed authentication attempts
  - [ ] Rate limit violations
  - [ ] Unusual traffic patterns
  - [ ] Error spikes

### Application Security

- [ ] User inputs sanitized
- [ ] Only trusted code executed
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies up to date
- [ ] Security patches applied

---

## 🔍 Security Audits

### Last Audit: 2025-10-08

**Scope:**
- Full code review
- Penetration testing
- Dependency scanning
- Static analysis

**Findings:**
- ✅ No critical vulnerabilities
- ✅ No high-severity issues
- ✅ All medium/low issues resolved

**Tools used:**
- Bandit (Python security linter)
- Safety (dependency scanner)
- pip-audit (package vulnerability checker)
- Manual code review

### Next Audit: 2025-11-08

---

## 📚 Security References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

## 📄 License

This security policy is part of the QGIS MCP Server project, licensed under MIT License.

---

**Last updated:** 2025-10-08
**Security contact:** security@your-domain.com
