<<<<<<< HEAD
# Dynamic_Load-Balancing-for-a-Smart-Grid
=======
# Smart Grid Load Balancer

A scalable system for dynamically balancing Electric Vehicle (EV) charging requests across multiple substations based on their real-time load, complete with a comprehensive observability stack.

## 🏗️ Architecture

The system consists of the following microservices:

### Core Services
- **Charge Request Service** (`charge_request_service`): Public entry point for EV charging requests
- **Load Balancer** (`load_balancer`): Dynamic load balancer that routes requests to the least loaded substation
- **Substation Services** (`substation_service`): Multiple replicas simulating charging substations

### Monitoring Stack
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboarding
- **Load Tester**: Performance testing tool

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for local development)

### Running the System

1. **Clone and navigate to the project:**
   ```bash
   cd smart-grid-load-balancer
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Wait for services to be healthy:**
   ```bash
   docker-compose ps
   ```

4. **Access the services:**
   - **Charge Request Service**: http://localhost:5005
   - **Load Balancer**: http://localhost:5004
   - **Substation 1**: http://localhost:5001
   - **Substation 2**: http://localhost:5002
   - **Substation 3**: http://localhost:5003
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3000 (admin/admin)

### Running Load Tests

1. **Start the load tester:**
   ```bash
   docker-compose --profile test run load_tester python test.py --requests 100 --concurrent 10
   ```

2. **Or run locally:**
   ```bash
   cd load_tester
   python test.py --requests 100 --concurrent 10 --url http://localhost:5005
   ```

## 📊 Monitoring

### Grafana Dashboard
Access the Smart Grid dashboard at http://localhost:3000 with credentials `admin/admin`.

The dashboard includes:
- Substation load monitoring
- Active charger counts
- Request rates and response times
- Load balancer routing decisions
- System performance metrics

### Key Metrics
- `current_load`: Current load in kW per substation
- `active_chargers`: Number of active charging sessions
- `charging_requests_total`: Total charging requests processed
- `load_balancer_requests_total`: Load balancer request count
- `charging_duration_seconds`: Charging session duration

## 🔧 API Endpoints

### Charge Request Service (Port 5005)
- `POST /charge` - Submit a charging request
- `GET /sessions` - Get active charging sessions
- `DELETE /sessions/{session_id}` - Stop a charging session
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Load Balancer (Port 5004)
- `POST /charge` - Route charging request to least loaded substation
- `GET /substations` - List registered substations
- `POST /substations` - Add a substation
- `DELETE /substations/{url}` - Remove a substation
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Substation Service (Ports 5001-5003)
- `POST /charge` - Start a charging session
- `DELETE /charge/{session_id}` - Stop a charging session
- `GET /status` - Get substation status
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## 📝 Example Usage

### Submit a Charging Request
```bash
curl -X POST http://localhost:5005/charge \
  -H "Content-Type: application/json" \
  -d '{
    "ev_id": "EV_1234",
    "requested_kw": 22,
    "duration_minutes": 120
  }'
```

### Check System Status
```bash
curl http://localhost:5004/status
```

### View Substation Metrics
```bash
curl http://localhost:5001/metrics
```

## 🧪 Load Testing

The load tester simulates realistic EV charging scenarios:

```bash
# Basic load test
python test.py --requests 100 --concurrent 10

# High load test
python test.py --requests 500 --concurrent 50 --ramp-up 120

# Custom URL
python test.py --url http://localhost:5005 --requests 200 --concurrent 20
```

### Load Test Parameters
- `--requests`: Number of requests to send
- `--concurrent`: Number of concurrent users
- `--ramp-up`: Ramp-up time in seconds
- `--url`: Target service URL
- `--save`: Save results to file

## 🔍 System Features

### Dynamic Load Balancing
- Real-time polling of substation metrics
- Intelligent routing to least loaded substation
- Automatic failover and recovery

### Observability
- Comprehensive Prometheus metrics
- Real-time Grafana dashboards
- Performance monitoring and alerting

### Scalability
- Multiple substation replicas
- Horizontal scaling capability
- Containerized microservices

### Fault Tolerance
- Health checks for all services
- Graceful degradation
- Automatic service recovery

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r charge_request_service/requirements.txt
pip install -r load_balancer/requirements.txt
pip install -r substation_service/requirements.txt

# Run services locally
python substation_service/main.py
python load_balancer/main.py
python charge_request_service/main.py
```

### Building Images
```bash
docker-compose build
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f load_balancer
```

## 📁 Project Structure
```
smart-grid-load-balancer/
├── charge_request_service/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── load_balancer/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── substation_service/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── load_tester/
│   ├── test.py
│   ├── Dockerfile
│   └── requirements.txt
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── dashboard.json
├── docker-compose.yml
└── README.md
```

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. **Port conflicts:**
   - Check if ports 5001-5005, 3000, 9090 are available
   - Modify ports in docker-compose.yml if needed

3. **Metrics not showing:**
   - Wait for services to be healthy
   - Check Prometheus targets at http://localhost:9090/targets

4. **Load balancer not routing:**
   - Verify substations are registered
   - Check load balancer logs: `docker-compose logs load_balancer`

### Health Checks
```bash
# Check all services
docker-compose ps

# Check specific service
curl http://localhost:5005/health
curl http://localhost:5004/health
curl http://localhost:5001/health
```

## 📈 Performance Analysis

The system provides comprehensive performance metrics:

- **Response Times**: Average, median, 95th percentile
- **Throughput**: Requests per second
- **Load Distribution**: How requests are distributed across substations
- **Error Rates**: Failed requests and error types
- **Resource Utilization**: CPU, memory, and network usage

## 🔐 Security Considerations

- All services run in isolated containers
- Network communication is restricted to internal Docker network
- No sensitive data is exposed in logs or metrics
- Health checks prevent routing to unhealthy services

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 
>>>>>>> 2440ffd (initial commit)
