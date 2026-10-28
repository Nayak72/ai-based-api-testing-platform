# Assertion Patterns for API Test Cases

## Status Code Assertions
```
type: status_code, operator: eq, value: 200   # happy path GET/POST action
type: status_code, operator: eq, value: 201   # POST create
type: status_code, operator: eq, value: 204   # DELETE success
type: status_code, operator: eq, value: 400   # malformed input
type: status_code, operator: eq, value: 401   # missing auth
type: status_code, operator: eq, value: 403   # wrong permissions
type: status_code, operator: eq, value: 404   # not found
type: status_code, operator: eq, value: 422   # validation error
type: status_code, operator: eq, value: 429   # rate limited
type: status_code, operator: lte, value: 399  # any success
type: status_code, operator: gte, value: 400  # any error
```

## JSON Path Assertions
```
# Field exists
type: json_path, path: $.id, operator: exists

# Array response not empty
type: json_path, path: $.items, operator: is_array

# Specific field value
type: json_path, path: $.status, operator: eq, value: "active"

# Field is not null
type: json_path, path: $.user_id, operator: not_null

# Total count > 0
type: json_path, path: $.total, operator: gt, value: 0

# No stack trace in error body (security)
type: json_path, path: $.detail, operator: not_contains, value: "Traceback"
```

## Header Assertions
```
# Content-Type is JSON
type: header, path: content-type, operator: contains, value: application/json

# Rate limit headers present
type: header, path: x-ratelimit-remaining, operator: exists
```

## Response Time Assertions
```
# Fast GET endpoint
type: response_time, operator: lt, value: 1000   # < 1 second

# Write operation
type: response_time, operator: lt, value: 3000   # < 3 seconds
```

## Security-Specific Assertion Patterns
- **BOLA check**: After accessing another user's resource, assert status_code eq 403 OR assert the returned user_id matches the requesting user's ID.
- **Auth check**: Remove Authorization header → assert status_code eq 401.
- **BFLA check**: Call admin endpoint with regular token → assert status_code eq 403.
- **Info leakage**: On 500 errors, assert body does NOT contain "Traceback", "Exception", "Error at line".
- **Mass assignment**: After PATCH with role=admin, GET the user and assert role still eq "user".

