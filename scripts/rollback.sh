#!/bin/bash

# Rollback script for Internship AI Assistant
# Usage: ./rollback.sh [environment] [backup_timestamp]
# Example: ./rollback.sh staging 20260101_120000
# Example: ./rollback.sh production latest

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
LOG_DIR="${BASE_DIR}/logs/rollback"
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

find_backup() {
    local env=$1
    local timestamp=$2

    if [ "$timestamp" == "latest" ]; then
        # Find the latest backup
        local backup_file=$(ls -t "${BACKUP_DIR}/${env}_database_"*.sql 2>/dev/null | head -1)
        if [ -z "$backup_file" ]; then
            log_error "No backup found for environment: $env"
            return 1
        fi

        # Extract timestamp from filename
        timestamp=$(basename "$backup_file" | sed "s/${env}_database_//" | sed "s/\.sql//")
        log_info "Found latest backup: $timestamp"
    fi

    # Check if backup files exist
    local db_backup="${BACKUP_DIR}/${env}_database_${timestamp}.sql"
    local redis_backup="${BACKUP_DIR}/${env}_redis_${timestamp}.rdb"
    local config_backup="${BACKUP_DIR}/${env}_config_${timestamp}.tar.gz"
    local containers_backup="${BACKUP_DIR}/${env}_containers_${timestamp}.log"

    if [ ! -f "$db_backup" ]; then
        log_error "Database backup not found: $db_backup"
        return 1
    fi

    echo "$timestamp"
    return 0
}

validate_backup() {
    local env=$1
    local timestamp=$2

    log_info "Validating backup $timestamp for $env..."

    local db_backup="${BACKUP_DIR}/${env}_database_${timestamp}.sql"

    # Check if backup file is valid SQL
    if ! head -n 10 "$db_backup" | grep -q "MySQL dump"; then
        log_warn "Backup file may not be a valid MySQL dump"
    fi

    # Check backup size
    local backup_size=$(stat -c%s "$db_backup")
    if [ "$backup_size" -lt 1024 ]; then
        log_error "Backup file is too small: $backup_size bytes"
        return 1
    fi

    log_info "Backup validation passed: $backup_size bytes"
    return 0
}

stop_services() {
    local env=$1

    log_info "Stopping $env services..."

    # Gracefully stop services
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" down --timeout 60

    log_info "Services stopped"
}

restore_database() {
    local env=$1
    local timestamp=$2

    log_info "Restoring database from backup: $timestamp"

    local db_backup="${BACKUP_DIR}/${env}_database_${timestamp}.sql"

    # Wait for MySQL to be ready
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" --silent; then
            log_info "MySQL is ready"
            break
        fi

        log_warn "Waiting for MySQL... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "MySQL is not ready after $max_attempts attempts"
        return 1
    fi

    # Drop and recreate database
    log_info "Recreating database..."
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T mysql mysql \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        -e "DROP DATABASE IF EXISTS internship_db; CREATE DATABASE internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # Restore backup
    log_info "Restoring data..."
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" exec -T mysql mysql \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        internship_db < "$db_backup"

    log_info "Database restored successfully"
}

restore_redis() {
    local env=$1
    local timestamp=$2

    local redis_backup="${BACKUP_DIR}/${env}_redis_${timestamp}.rdb"

    if [ ! -f "$redis_backup" ]; then
        log_warn "Redis backup not found, skipping Redis restore"
        return 0
    fi

    log_info "Restoring Redis from backup..."

    # Stop Redis
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" stop redis

    # Restore RDB file
    cp "$redis_backup" "${BASE_DIR}/data/redis/dump.rdb"

    # Start Redis
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" start redis

    log_info "Redis restored successfully"
}

restore_configuration() {
    local env=$1
    local timestamp=$2

    local config_backup="${BACKUP_DIR}/${env}_config_${timestamp}.tar.gz"

    if [ ! -f "$config_backup" ]; then
        log_warn "Configuration backup not found, skipping config restore"
        return 0
    fi

    log_info "Restoring configuration from backup..."

    # Extract backup
    tar xzf "$config_backup" -C "$BASE_DIR" --overwrite

    log_info "Configuration restored successfully"
}

restore_previous_version() {
    local env=$1

    log_info "Restoring previous version of services..."

    # Use previous image tags from backup
    local containers_backup=$(ls -t "${BACKUP_DIR}/${env}_containers_"*.log 2>/dev/null | head -1)
    if [ -f "$containers_backup" ]; then
        log_info "Found containers backup: $(basename "$containers_backup")"

        # Extract image versions from backup (simplified)
        local backend_image=$(grep "backend" "$containers_backup" | head -1 | awk '{print $2}' | cut -d':' -f2)
        local frontend_image=$(grep "frontend" "$containers_backup" | head -1 | awk '{print $2}' | cut -d':' -f2)

        if [ -n "$backend_image" ]; then
            log_info "Previous backend version: $backend_image"
            sed -i "s/BACKEND_IMAGE_TAG=.*/BACKEND_IMAGE_TAG=$backend_image/" "${BASE_DIR}/.env.${env}"
        fi

        if [ -n "$frontend_image" ]; then
            log_info "Previous frontend version: $frontend_image"
            sed -i "s/FRONTEND_IMAGE_TAG=.*/FRONTEND_IMAGE_TAG=$frontend_image/" "${BASE_DIR}/.env.${env}"
        fi
    fi

    # Pull previous images
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" pull

    # Start services
    docker-compose -f "${BASE_DIR}/docker-compose.${env}.yml" up -d

    log_info "Previous version restored"
}

health_check() {
    local env=$1

    log_info "Performing health checks after rollback..."

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

notify_rollback() {
    local env=$1
    local timestamp=$2
    local status=$3

    log_info "Sending rollback notification..."

    # Send Slack notification
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        local color="warning"
        local message="🔄"

        if [ "$status" == "success" ]; then
            color="good"
            message="✅"
        elif [ "$status" == "failed" ]; then
            color="danger"
            message="❌"
        fi

        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Rollback ${message}\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$env\", \"short\": true},
                        {\"title\": \"Backup Timestamp\", \"value\": \"$timestamp\", \"short\": true},
                        {\"title\": \"Status\", \"value\": \"$status\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$(date)\", \"short\": true}
                    ]
                }]
            }" > /dev/null 2>&1
    fi

    log_info "Notification sent"
}

main() {
    # Parse arguments
    local env="${1:-production}"
    local timestamp="${2:-latest}"

    # Validate environment
    if [[ ! "$env" =~ ^(staging|production)$ ]]; then
        log_error "Invalid environment: $env. Must be 'staging' or 'production'"
        exit 1
    fi

    log_info "Starting rollback for $env to backup: $timestamp"
    log_info "Working directory: $BASE_DIR"

    # Load environment variables
    if [ -f "${BASE_DIR}/.env.${env}" ]; then
        source "${BASE_DIR}/.env.${env}"
    else
        log_error "Environment file not found: ${BASE_DIR}/.env.${env}"
        exit 1
    fi

    # Create log directory
    mkdir -p "$LOG_DIR"

    # Start rollback
    local start_time=$(date +%s)

    # Step 1: Find backup
    timestamp=$(find_backup "$env" "$timestamp")
    if [ $? -ne 0 ]; then
        log_error "Failed to find backup"
        exit 1
    fi

    # Step 2: Validate backup
    validate_backup "$env" "$timestamp"

    # Step 3: Stop services
    stop_services "$env"

    # Step 4: Restore database
    restore_database "$env" "$timestamp"

    # Step 5: Restore Redis (if available)
    restore_redis "$env" "$timestamp"

    # Step 6: Restore configuration (if available)
    restore_configuration "$env" "$timestamp"

    # Step 7: Restore previous version
    restore_previous_version "$env"

    # Step 8: Health check
    health_check "$env"

    # Calculate rollback time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Step 9: Send success notification
    notify_rollback "$env" "$timestamp" "success"

    log_info "Rollback completed successfully!"
    log_info "Total time: ${duration} seconds"

    # Show rollback summary
    echo ""
    echo "========================================"
    echo "Rollback Summary"
    echo "========================================"
    echo "Environment: $env"
    echo "Backup Timestamp: $timestamp"
    echo "Status: ✅ Success"
    echo "Duration: ${duration} seconds"
    echo "Timestamp: $(date)"
    echo "Backup Used: ${BACKUP_DIR}/${env}_*_${timestamp}.*"
    echo "Logs: ${LOG_DIR}/"
    echo "========================================"

    # List restored files
    echo ""
    echo "Restored files:"
    ls -la "${BACKUP_DIR}/${env}_*_${timestamp}.*" 2>/dev/null || echo "No backup files found"

    return 0
}

# Handle errors
trap 'log_error "Rollback failed at line $LINENO"; notify_rollback "${env:-unknown}" "${timestamp:-unknown}" "failed"; exit 1' ERR

# Run main function
main "$@"

# Log completion
log_info "Rollback script finished"