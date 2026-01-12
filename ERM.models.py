# DATABASE RELATIONSHIP DIAGRAM:
# 
# Destination (1) ──< (Many) Event ──< (Many) DeliveryAttempt
#     |                    |                        |
#     └─ id                └─ id                    └─ event_id (FK)
#     └─ url               └─ destination_id (FK)   └─ status
#     └─ secret_key        └─ payload               └─ response_code
#     └─ is_active         └─ status                └─ response_body
#     └─ created_at        └─ attempts              └─ timestamp
#                          └─ created_at
# 
# 
# REAL WORLD EXAMPLE:
# -------------------
# 
# 1. You create a Destination:
#    - url = "https://discord.com/api/webhooks/123/abc"
#    - secret_key = "xyz789"
# 
# 2. GitHub sends you a webhook, you create an Event:
#    - destination = Destination #1 (from step 1)
#    - payload = {"action": "push", "commits": [...]}
#    - status = "PENDING"
#    - attempts = 0
# 
# 3. Celery worker tries to deliver (Attempt #1):
#    - Create DeliveryAttempt:
#      - event = Event #1
#      - response_status_code = 500 (Discord is down!)
#      - response_body = "Internal Server Error"
#      - status = "FAILED"
#    - Update Event: attempts = 1
# 
# 4. Celery retries 5 minutes later (Attempt #2):
#    - Create another DeliveryAttempt:
#      - event = Event #1 (same event)
#      - response_status_code = 200 (Success!)
#      - response_body = '{"ok": true}'
#      - status = "SUCCESS"
#    - Update Event: status = "SUCCESS"
# 
# 5. Now you can query:
#    - event.attempts.all() → See both attempts (the 500 and the 200)
#    - destination.events.filter(status='SUCCESS') → See all successful events
# 
# ============================================================================
"""GitHub → [Event Model] → Discord
(Source)   (Our System)   (Destination)"""