#!/bin/bash

# Function to start the backend service
start_backend() {
    echo "Starting backend service..."
    cd app/backend
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ../..
    echo "Backend service started with PID: $BACKEND_PID"
}

# Function to start the frontend service
start_frontend() {
    echo "Starting frontend service..."
    cd app/frontend
    if [ -f "package.json" ]; then
        npm install
        npm run dev &
    else
        echo "Error: package.json not found in frontend directory"
        exit 1
    fi
    FRONTEND_PID=$!
    cd ../..
    echo "Frontend service started with PID: $FRONTEND_PID"
}

# Function to stop all services
stop_services() {
    echo "Stopping all services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    echo "All services stopped"
}

# Handle script termination
trap stop_services EXIT

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo "Options:"
    echo "  -b, --backend    Start only the backend service"
    echo "  -f, --frontend   Start only the frontend service"
    echo "  -a, --all        Start both services (default)"
    echo "  -h, --help       Show this help message"
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    # Default: start both services
    start_backend
    start_frontend
    wait
else
    case "$1" in
        b|backend)
            start_backend
            wait
            ;;
        f|frontend)
            start_frontend
            wait
            ;;
        a|all)
            start_backend
            start_frontend
            wait
            ;;
        h|help)
            show_usage
            ;;
        *)
            echo "Invalid option: $1"
            show_usage
            exit 1
            ;;
    esac
fi
