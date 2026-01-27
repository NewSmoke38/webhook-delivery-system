# Webhook Delivery System

A fault-tolerant, asynchronous webhook delivery platform designed to handle high-throughput event ingestion and reliable delivery to external destinations. Built with an emphasis on scalability, data integrity, and security.

## System Architecture

```mermaid
sequenceDiagram
    participant Client
    participant API as Django API
    participant DB as PostgreSQL
    participant Queue as Redis
    participant Worker as Celery Worker
    participant Dest as External Destination

    Client->>API: POST /api/events (Webhook)
    API->>DB: Persist Event (Status: PENDING)
    API->>Queue: Enqueue Delivery Task
    API-->>Client: 202 Accepted (Async)

    Note right of Client: Client is released immediately

    Queue->>Worker: Pop Task
    Worker->>DB: Fetch Event & Destination
    Worker->>Dest: POST /webhook-endpoint (HMAC Signed)
    
    alt Success
        Dest-->>Worker: 200 OK
        Worker->>DB: Update Event (SUCCESS)
        Worker->>DB: Log DeliveryAttempt
    else Failure
        Dest-->>Worker: 500 / Timeout
        Worker->>Queue: Retry with Exponential Backoff
        Worker->>DB: Log Retry Attempt
    end
```

## Core Features

*   **Asynchronous Processing**: Decouples ingestion from delivery using Celery and Redis, ensuring sub-50ms API response times regardless of downstream latency.
*   **Reliable Delivery Engine**: Implements exponential backoff retry strategies (1m, 2m, 4m) to handle external service outages gracefully.
*   **Security**: authenticates payload integrity using HMAC-SHA256 signatures, preventing replay attacks and tampering.
*   **Observability**: Full audit logging of every delivery attempt, response code, and latency in a normalized PostgreSQL schema.
*   **Scalability**: Dockerized microservices architecture allowing independent scaling of ingestion handling (API) and delivery throughput (Workers).

## Tech Stack

*   **Backend**: Python, Django, Django REST Framework
*   **Async Task Queue**: Celery
*   **Message Broker**: Redis
*   **Database**: PostgreSQL
*   **Infrastructure**: Docker, Docker Compose


