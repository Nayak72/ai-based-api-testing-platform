# HTTP Status Codes for API Testing

## 2xx — Success
| Code | Meaning | When to Assert It |
|------|---------|-------------------|
| 200 OK | Standard success | GET, POST (actions), PUT, PATCH |
| 201 Created | Resource created | POST creating a resource; check Location header |
| 204 No Content | Success, no body | DELETE, PUT when returning no body |

## 3xx — Redirection
| Code | Meaning | Testing Note |
|------|---------|--------------|
| 301/302 | Permanent/Temporary redirect | Re-validate target URL via TargetGuard |
| 304 Not Modified | Cached; no body | Conditional GET with ETag/If-Modified-Since |

## 4xx — Client Errors
| Code | Meaning | Triggers |
|------|---------|---------|
| 400 Bad Request | Malformed syntax, invalid types | Missing field, wrong type, invalid JSON |
| 401 Unauthorized | Missing or invalid auth | No/expired/tampered token |
| 403 Forbidden | Authenticated but not authorized | Access to another user's resource; wrong role |
| 404 Not Found | Resource absent (or hidden) | Non-existent ID |
| 405 Method Not Allowed | HTTP method not supported | GET on a POST-only endpoint |
| 409 Conflict | State conflict | Duplicate resource, optimistic locking |
| 413 Payload Too Large | Body too big | Oversized upload |
| 422 Unprocessable Entity | Syntactically valid but semantically wrong | Failed business validation |
| 429 Too Many Requests | Rate limited | Rapid sequential calls; check Retry-After header |

## 5xx — Server Errors (almost always bugs)
| Code | Meaning | Test Signal |
|------|---------|------------|
| 500 Internal Server Error | Unhandled exception | Sending malformed input should give 400, not 500 |
| 502/503 | Gateway/upstream unavailable | Transient; retry once |
| 504 | Gateway timeout | Upstream slow |

## Key Assertions
- Malformed input → expect 400 or 422, **never 500**.
- No auth header → expect 401, **not 403**.
- Authenticated, wrong resource → expect 403 (or 404 if hiding existence).
- 500 on any user-controlled input = a bug worth reporting.

