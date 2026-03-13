# Production-Ready Data Engineering System

This project is an end-to-end data engineering system featuring a Mock Market Data API, an ETL Pipeline, and a PostgreSQL database, all containerized with Docker.

## Architecture Diagram

```mermaid
graph TD
    A[Source API (FastAPI)] -- JSON Data --> B[ETL Pipeline (Python)]
    B -- Processed Records --> C[PostgreSQL Database]
    B -- Validation Failures --> D[Log Analytics]
    subgraph Docker Network
        A
        B
        C
    end
```

## Setup Instructions

1.  Clone the repository.
2.  Copy `.env.example` to `.env`.
    ```bash
    cp .env.example .env
    ```
3.  Ensure Docker and Docker Compose are installed.

## How to Run the System

Run the following command in the project root:

```bash
docker-compose up --build
```

## API Example

Endpoint: `GET /v1/market-data`

Response Example:
```json
[
  {
    "instrument_id": "AAPL",
    "price": 172.21,
    "volume": 120.5,
    "timestamp": "2026-03-12T10:00:00Z"
  }
]
```

### Fault Injection (Chaos Engineering)

The API implements **fault injection for 5% of requests** to simulate real-world failures and test system resilience:

- **2.5% of requests**: Return HTTP 500 Internal Server Error
- **2.5% of requests**: Return malformed JSON data (e.g., price field as string "INVALID_PRICE" instead of float)

This helps validate the ETL pipeline's error handling and retry mechanisms.

## Database Schema

Table: `market_data`

| Column | Type | Description |
| :--- | :--- | :--- |
| `instrument_id` | TEXT | Stock or Crypto ticker |
| `price` | FLOAT | Last traded price |
| `volume` | FLOAT | Traded volume in interval |
| `timestamp` | TIMESTAMP | Record time (UTC) |
| `vwap` | FLOAT | Volume Weighted Average Price (per batch) |
| `is_outlier` | BOOLEAN | True if price > 15% from batch average |

**Primary Key**: `(instrument_id, timestamp)`

## ETL Pipeline Details

The ETL pipeline continuously processes data from the API with the following stages:

### Extraction
- **Polling**: Periodically fetches data from the API endpoint
- **Error Handling**: Manages network timeouts, HTTP failures, and malformed responses
- **Retry Logic**: Implements exponential backoff for failed requests (up to 3 retries)

### Schema Validation
- **Pydantic Models**: Validates incoming records against expected schema
- **Invalid Record Handling**: Drops records that fail validation before further processing

### Transformation & Processing
- **VWAP Calculation**: Computes Volume Weighted Average Price per instrument: `VWAP = Σ(price × volume) / Σ(volume)`
- **Outlier Detection**: Flags records where price deviates more than 15% from batch average

### Load & Logging
- **Database Inserts**: Stores processed records with `ON CONFLICT DO NOTHING` for idempotency
- **Structured Logging**: Logs `records_processed`, `records_dropped`, and `execution_time_seconds` in JSON format

## Docker Infrastructure

The system runs on three Docker services:

- **api**: FastAPI service with its own Dockerfile, exposes port 8000
- **etl**: Python ETL pipeline with its own Dockerfile, runs continuously
- **db**: PostgreSQL database with health checks

### Docker Networking
Containers communicate through Docker's internal network:
- ETL connects to PostgreSQL using service name `db` instead of `localhost`
- API is accessible via service name `api` within the network

### Database Initialization
The `market_data` table is created automatically on container startup using `init.sql` script.

## System Flow Description

1. **Data Generation**: FastAPI API generates synthetic market data for multiple instruments
2. **Fault Injection**: 5% of API requests include intentional failures (HTTP 500 or malformed data)
3. **ETL Processing**: Pipeline polls API, validates data with Pydantic, calculates VWAP and detects outliers
4. **Data Storage**: Processed records are inserted into PostgreSQL with duplicate prevention
5. **Monitoring**: Structured logs track processing metrics and errors

## ETL Log Examples

The ETL pipeline produces structured JSON logs:

```json
{"timestamp": "2026-03-13T15:01:55.470098", "level": "INFO", "message": "Batch processed", "logger": "__main__", "records_processed": 4, "records_dropped": 0, "execution_time_seconds": 2.1363}
```

### Error Handling Logs
```json
{"timestamp": "2026-03-13T15:01:37.123456", "level": "WARNING", "message": "Attempt 1 failed: HTTPConnectionPool(host='api', port=8000): Max retries exceeded...", "logger": "__main__"}
{"timestamp": "2026-03-13T15:01:39.789012", "level": "WARNING", "message": "Validation failed for record: {'instrument_id': 'TSLA', 'price': 'INVALID_PRICE', ...}. Error: 1 validation error", "logger": "__main__"}
```

## Database Query Examples

### Check Record Count
```sql
SELECT COUNT(*) FROM market_data;
-- Output: 1003
```

### View Recent Records
```sql
SELECT instrument_id, price, volume, vwap, is_outlier, timestamp 
FROM market_data 
ORDER BY timestamp DESC 
LIMIT 5;
```

Sample output:
```
instrument_id | price  | volume | vwap   | is_outlier | timestamp
AAPL         | 161.32 | 196.85 | 161.32 | false      | 2026-03-13T15:01:55Z
BTC-USD      | 6301.28| 158.34 | 6301.28| false      | 2026-03-13T15:01:55Z
ETH-USD      | 2564.52| 536.52 | 2564.52| false      | 2026-03-13T15:01:55Z
TSLA         | 174.07 | 796.94 | 174.07 | false      | 2026-03-13T15:01:55Z
```

### Find Outliers
```sql
SELECT * FROM market_data WHERE is_outlier = true;
```

### VWAP Analysis
```sql
SELECT instrument_id, AVG(vwap) as avg_vwap, COUNT(*) as records
FROM market_data 
GROUP BY instrument_id;
```

## System Monitoring

### Health Checks
- **API**: `GET http://localhost:8000/v1/market-data` (should return JSON)
- **Database**: Check connection and table existence
- **ETL**: Monitor log output for "Batch processed" messages

### Performance Metrics
- **Throughput**: Records processed per minute
- **Error Rate**: Percentage of failed batches
- **Latency**: Average batch processing time

### Docker Monitoring
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs api
docker-compose logs etl
docker-compose logs db
```

## Troubleshooting

### Common Issues

**ETL can't connect to API:**
- Ensure API is running on port 8000
- Check API_URL environment variable
- Verify Docker network (for containerized setup)

**Database connection errors:**
- For Docker: Wait for PostgreSQL health check
- For local: Ensure SQLite file permissions
- Check DB credentials in `.env`

**Port conflicts:**
- Kill processes using port 8000: `netstat -ano | findstr :8000`
- Use different ports if needed

**ETL validation errors:**
- Check API is returning valid JSON
- Review Pydantic model constraints
- Monitor for chaos injection (expected 5% failure rate)

### Debug Commands
```bash
# Test API directly
curl http://localhost:8000/v1/market-data

# Check database
python -c "import sqlite3; conn=sqlite3.connect('market_data.db'); print('Connected'); conn.close()"

# View ETL logs
tail -f etl/logs/pipeline.log  # If logging to file
```

## System Design Questions

### 1. Scaling for 1 Billion Events per Day

To scale for ~12,000 events per second (1 billion/day):
- **Ingestion Layer**: Replace the polling ETL with a message broker like **Apache Kafka** or **AWS Kinesis**. The API would push events to a "raw-data" topic.
- **Processing Layer**: Use distributed streaming frameworks like **Apache Spark Streaming** or **Apache Flink** to consume from Kafka and perform windowed transformations (VWAP).
- **Storage**: Move from a single relational DB to a **Data Lake (S3/GCS)** for raw storage and a high-performance **NoSQL/OLAP database** (like ClickHouse, Druid, or Cassandra) for queryable processed data.
- **Compute**: Deploy the processing jobs on a Kubernetes cluster (EKS/GKE) for elastic scaling.

### 2. Monitoring

- **Health Checks**:
  - API: `/health` or endpoint verification (already in docker-compose).
  - ETL: Use a heartbeat mechanism or push metrics to a gateway.
- **Metrics & Tools**:
  - Use **Prometheus** to collect metrics like `records_processed`, `error_rate`, and `latency`.
  - Use **Grafana** for visualization.
  - Implement alerts (e.g., PagerDuty) if the pipeline lag increases or success rate drops.

### 3. Recovery / Idempotency

- **Idempotency**: The use of a composite Primary Key `(instrument_id, timestamp)` with `ON CONFLICT DO NOTHING` ensures that if a batch is partially processed and retried, duplicates are not created.
- **Checkpointing**: In a streaming system, Kafka consumer offsets ensure we resume from the last successfully acknowledged record.
- **Atomic Transactions**: Use database transactions for batch inserts to ensure either all records in a batch are committed or none are (all-or-nothing).
