# REST API Conventions for Test Generation

## HTTP Methods
| Method | Purpose | Idempotent | Body |
|--------|---------|------------|------|
| GET | Read resource | Yes | No |
| POST | Create / trigger action | No | Yes |
| PUT | Full replace | Yes | Yes |
| PATCH | Partial update | Ideally | Yes (partial) |
| DELETE | Remove | Yes | Usually no |

## URL Patterns
- `/resources` — collection endpoint (GET=list, POST=create)
- `/resources/{id}` — single item (GET, PUT, PATCH, DELETE)
- `/resources/{id}/sub` — nested collection

## Request Headers to Test
- `Content-Type: application/json` — required for POST/PUT/PATCH
- `Authorization: Bearer {token}` — required for protected endpoints
- `Accept: application/json` — good practice
- Missing Content-Type on a JSON body → should give 400 or 415

## Common Functional Assertions
- GET collection → 200 + JSON array or paginated object
- POST create with valid body → 201 + created object (or at minimum an ID)
- GET non-existent ID → 404
- DELETE then GET → 404
- POST missing required field → 400 or 422
- PUT/PATCH with wrong type for a field → 400 or 422
- GET with query filter → only matching records returned

## Pagination Conventions
- `?page=1&page_size=20` or `?limit=20&offset=0`
- Response should include total count (`total`, `count`, or in headers)
- Negative page → 400; page_size > max → capped server-side

