# PaymentService (MVP)

FastAPI-based minimal Payment Service implementing:
- POST /payments/intent: Create a mock payment intent and return a clientSecret
- GET /payments/{paymentId}: Retrieve payment intent status
- POST /payments/webhook: Simulate a payment gateway webhook to update payment status

Storage: In-memory dictionary. This is for MVP/dev only.

OpenAPI: See openapi/payment.yaml; the service aligns with the PaymentIntent schema and endpoints for intent creation and retrieval. The webhook is an MVP addition to simulate gateway callbacks.

Run locally:
1. Install dependencies:
   pip install -r requirements.txt
2. Start the server:
   python serve.py
3. Docs:
   http://localhost:8104/docs

Example:
- Create intent:
  curl -X POST http://localhost:8104/payments/intent -H "Content-Type: application/json" -d '{"orderId":"ord_123","method":"card","amount":250.00,"currency":"INR"}'

- Get status:
  curl http://localhost:8104/payments/<paymentId>

- Simulate webhook (succeeded):
  curl -X POST http://localhost:8104/payments/webhook -H "Content-Type: application/json" -d '{"type":"payment_intent.succeeded","paymentId":"<paymentId>"}'
