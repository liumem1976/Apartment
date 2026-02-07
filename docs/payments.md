# Payments API

## OpenAPI fragment (YAML)

```yaml
openapi: 3.0.3
info:
  title: LAN Apartment Billing - Payments
  version: 1.0.0
paths:
  /api/v1/payments:
    post:
      summary: Record a payment
      description: |
        Create a `Payment` record. The endpoint accepts form-encoded POST data
        (`application/x-www-form-urlencoded`) or `multipart/form-data`.
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                bill_id:
                  type: integer
                unit_id:
                  type: integer
                amount:
                  type: number
                  format: decimal
                method:
                  type: string
                reference:
                  type: string
              required:
                - amount
      responses:
        "200":
          description: Payment created
          content:
            application/json:
              schema:
                type: object
                properties:
                  payment_id:
                    type: integer
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

## Simple client examples

- curl

```bash
# Record a payment for a bill
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "bill_id=123" \
  -d "amount=100.00" \
  -d "method=card" \
  -d "reference=txn-20260207-001"

# Record a unit-level payment (unassigned to a bill)
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "unit_id=45" \
  -d "amount=50.00" \
  -d "method=cash"
```

- Python (requests)

```python
import requests

BASE = "http://localhost:8000"
TOKEN = "<your_jwt_token>"

headers = {"Authorization": f"Bearer {TOKEN}"}

# example: attach to a bill
data = {"bill_id": 123, "amount": "100.00", "method": "card", "reference": "txn-001"}
resp = requests.post(f"{BASE}/api/v1/payments", headers=headers, data=data)
resp.raise_for_status()
print(resp.json())

# example: unit-level credit
data = {"unit_id": 45, "amount": "50.00", "method": "cash"}
resp = requests.post(f"{BASE}/api/v1/payments", headers=headers, data=data)
print(resp.json())
```

Notes:
- The API requires an authenticated user; include `Authorization: Bearer <token>`.
- If you use curl with `-F` instead of `-d` the server will also accept `multipart/form-data`.
- Response body on success: `{ "payment_id": <int> }`.
