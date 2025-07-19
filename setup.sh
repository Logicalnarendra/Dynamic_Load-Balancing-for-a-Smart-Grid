#!/bin/bash

# Smart Grid Load Balancer Setup Script
# This script sets up the system and registers substations with the load balancer

set -e

echo "🚀 Setting up Smart Grid Load Balancer..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for service to be ready
wait_for_service() {
    local service_url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url/health" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within expected time"
    return 1
}

# Function to register substation with load balancer
register_substation() {
    local substation_url=$1
    local substation_name=$2
    
    print_status "Registering $substation_name with load balancer..."
    
    if curl -s -X POST "http://localhost:5004/substations" \
        -H "Content-Type: application/json" \
        -d "{\"substation_url\": \"$substation_url\"}" > /dev/null 2>&1; then
        print_success "$substation_name registered successfully"
    else
        print_error "Failed to register $substation_name"
        return 1
    fi
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down --remove-orphans

# Build and start services
print_status "Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
print_status "Waiting for services to start..."

# Wait for substations
wait_for_service "http://localhost:5001" "Substation 1"
wait_for_service "http://localhost:5002" "Substation 2"
wait_for_service "http://localhost:5003" "Substation 3"

# Wait for load balancer
wait_for_service "http://localhost:5004" "Load Balancer"

# Wait for charge request service
wait_for_service "http://localhost:5005" "Charge Request Service"

# Register substations with load balancer
print_status "Registering substations with load balancer..."

register_substation "http://substation_1:5000" "Substation 1"
register_substation "http://substation_2:5000" "Substation 2"
register_substation "http://substation_3:5000" "Substation 3"

# Wait for Prometheus and Grafana
print_status "Waiting for monitoring services..."

# Wait for Prometheus
if wait_for_service "http://localhost:9090" "Prometheus"; then
    print_success "Prometheus is ready!"
else
    print_warning "Prometheus may still be starting..."
fi

# Wait for Grafana
if wait_for_service "http://localhost:3000" "Grafana"; then
    print_success "Grafana is ready!"
else
    print_warning "Grafana may still be starting..."
fi

# Display system status
print_status "Checking system status..."
if curl -s "http://localhost:5004/status" > /dev/null 2>&1; then
    print_success "Load balancer is operational"
else
    print_error "Load balancer is not responding"
fi

# Display service URLs
echo ""
echo "🎉 Smart Grid Load Balancer is ready!"
echo ""
echo "📊 Service URLs:"
echo "  Charge Request Service: http://localhost:5005"
echo "  Load Balancer:          http://localhost:5004"
echo "  Substation 1:           http://localhost:5001"
echo "  Substation 2:           http://localhost:5002"
echo "  Substation 3:           http://localhost:5003"
echo "  Prometheus:             http://localhost:9090"
echo "  Grafana:                http://localhost:3000 (admin/admin)"
echo ""
echo "🧪 To run a load test:"
echo "  docker-compose --profile test run load_tester python test.py --requests 100 --concurrent 10"
echo ""
echo "📝 Example API call:"
echo "  curl -X POST http://localhost:5005/charge \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"ev_id\": \"EV_1234\", \"requested_kw\": 22}'"
echo ""

# Check if all services are healthy
print_status "Checking service health..."
docker-compose ps

print_success "Setup complete! 🚀" 