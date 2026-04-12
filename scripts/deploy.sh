#!/bin/bash

# Deployment script for Internship AI Assistant
# Usage: ./deploy.sh [environment] [version]
# Example: ./deploy.sh staging latest
# Example: ./deploy.sh production v1.0.0

set -e  # Exit on error
set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_DIR="/opt/internship-ai"
BACKUP_DIR="${BASE_DIR}/backups"
LOG_DIR="${BASE_DIR}/logs/deployment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function definitions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check directory exists
    if [ ! -d "$BASE_DIR" ]; then
        log_error "Base directory $BASE_DIR does not exist"
        exit 1
    fi

    log_info "Requirements check passed"
}

backup_current() {
    local env=$1
    log_info "Backing up current $env deployment..."

    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"

    # Backup Docker container state
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" ps > "${BACKUP_DIR}/${env}_containers_${TIMESTAMP}.log" 2>&1

    # Backup database
    if [ "$env" == "production" ] || [ "$env" == "staging" ]; then
        log_info "Backing up database..."
        docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T mysql mysqldump \
            -u internship \
            -p"${MYSQL_PASSWORD}" \
            internship_db > "${BACKUP_DIR}/${env}_database_${TIMESTAMP}.sql" 2>>"${LOG_DIR}/backup_${TIMESTAMP}.log"

        # Backup Redis (if enabled)
        docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T redis redis-cli \
            -a "${REDIS_PASSWORD}" \
            SAVE >>"${LOG_DIR}/backup_${TIMESTAMP}.log" 2>&1
        cp "${BASE_DIR}/data/redis/dump.rdb" "${BACKUP_DIR}/${env}_redis_${TIMESTAMP}.rdb" 2>>"${LOG_DIR}/backup_${TIMESTAMP}.log"
    fi

    # Backup configuration files
    tar czf "${BACKUP_DIR}/${env}_config_${TIMESTAMP}.tar.gz" \
        "${BASE_DIR}/.env.${env}" \
        "${BASE_DIR}/nginx/conf.d/" \
        "${BASE_DIR}/nginx/nginx.conf" \
        2>>"${LOG_DIR}/backup_${TIMESTAMP}.log"

    # Clean old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "*${env}*" -type f -mtime +7 -delete

    log_info "Backup completed: ${BACKUP_DIR}/${env}_*_${TIMESTAMP}.*"
}

pull_images() {
    local env=$1
    local version=$2

    log_info "Pulling Docker images for $env (version: $version)..."

    # Update image tags in .env file
    if [ -n "$version" ] && [ "$version" != "latest" ]; then
        sed -i "s/BACKEND_IMAGE_TAG=.*/BACKEND_IMAGE_TAG=$version/" "${BASE_DIR}/.env.${env}"
        sed -i "s/FRONTEND_IMAGE_TAG=.*/FRONTEND_IMAGE_TAG=$version/" "${BASE_DIR}/.env.${env}"
    fi

    # Pull images
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" pull
    log_info "Docker images pulled successfully"
}

run_migrations() {
    local env=$1

    log_info "Running database migrations for $env..."

    # Wait for database to be ready
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T mysql mysqladmin ping -h localhost -u internship -p"${MYSQL_PASSWORD}" --silent; then
            log_info "Database is ready"
            break
        fi

        log_warn "Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Database is not ready after $max_attempts attempts"
        return 1
    fi

    # Run migrations
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T backend alembic upgrade head
    log_info "Database migrations completed"
}

deploy_services() {
    local env=$1

    log_info "Deploying services for $env..."

    # Stop and remove old containers
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" down --remove-orphans

    # Start new containers
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" up -d

    log_info "Services deployed successfully"
}

health_check() {
    local env=$1

    log_info "Performing health checks for $env..."

    local max_attempts=30
    local attempt=1
    local health_endpoint=""

    if [ "$env" == "production" ]; then
        health_endpoint="https://internship.example.com/health"
    elif [ "$env" == "staging" ]; then
        health_endpoint="http://staging.internship.example.com/health"
    else
        health_endpoint="http://localhost:8000/health"
    fi

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_endpoint" > /dev/null; then
            log_info "Health check passed"
            return 0
        fi

        log_warn "Health check failed (attempt $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

notify_deployment() {
    local env=$1
    local version=$2
    local status=$3

    log_info "Sending deployment notification..."

    # Send Slack notification
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        local color="good"
        local message="✅"

        if [ "$status" != "success" ]; then
            color="danger"
            message="❌"
        fi

        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Deployment ${message}\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$env\", \"short\": true},
                        {\"title\": \"Version\", \"value\": \"$version\", \"short\": true},
                        {\"title\": \"Status\", \"value\": \"$status\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$(date)\", \"short\": true}
                    ]
                }]
            }" > /dev/null 2>&1
    fi

    # Send email notification (simplified)
    if [ -n "${EMAIL_RECIPIENTS}" ]; then
        echo "Deployment $status for $env ($version) at $(date)" | \
        mail -s "Deployment $status: $env" "${EMAIL_RECIPIENTS}"
    fi

    log_info "Notification sent"
}

main() {
    # Parse arguments
    local env="${1:-staging}"
    local version="${2:-latest}"

    # Validate environment
    if [[ ! "$env" =~ ^(staging|production)$ ]]; then
        log_error "Invalid environment: $env. Must be 'staging' or 'production'"
        exit 1
    fi

    log_info "Starting deployment to $env (version: $version)"
    log_info "Working directory: $BASE_DIR"

    # Load environment variables
    if [ -f "${BASE_DIR}/.env.${env}" ]; then
        source "${BASE_DIR}/.env.${env}"
    else
        log_error "Environment file not found: ${BASE_DIR}/.env.${env}"
        exit 1
    fi

    # Check requirements
    check_requirements

    # Create log directory
    mkdir -p "$LOG_DIR"

    # Start deployment
    local start_time=$(date +%s)

    # Step 1: Backup current deployment
    backup_current "$env"

    # Step 2: Pull new images
    pull_images "$env" "$version"

    # Step 3: Run database migrations
    if [ "$env" == "production" ] || [ "$env" == "staging" ]; then
        run_migrations "$env"
    fi

    # Step 4: Deploy services
    deploy_services "$env"

    # Step 5: Health check
    health_check "$env"

    # Calculate deployment time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Step 6: Send success notification
    notify_deployment "$env" "$version" "success"

    log_info "Deployment completed successfully!"
    log_info "Total time: ${duration} seconds"

    # Show deployment summary
    echo ""
    echo "========================================"
    echo "Deployment Summary"
    echo "========================================"
    echo "Environment: $env"
    echo "Version: $version"
    echo "Status: ✅ Success"
    echo "Duration: ${duration} seconds"
    echo "Timestamp: $(date)"
    echo "Backup: ${BACKUP_DIR}/${env}_*_${TIMESTAMP}.*"
    echo "Logs: ${LOG_DIR}/"
    echo "========================================"

    return 0
}

# Handle errors
trap 'log_error "Deployment failed at line $LINENO"; notify_deployment "${env:-unknown}" "${version:-unknown}" "failed"; exit 1' ERR

# Run main function
main "$@"

# Log completion
log_info "Deployment script finished"