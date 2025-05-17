# devweek-2025

## Running the Application

This project consists of a frontend and backend service. You can run them separately or together using the provided shell script.

### Prerequisites

- Python 3.x
- Node.js and npm
- pip (Python package manager)

### Running the Services

Use the following commands to run the services:

```bash
# Run both frontend and backend services
./run.sh all

# Run only the backend service
./run.sh backend

# Run only the frontend service
./run.sh frontend

# Show help
./run.sh help
```

### Service Details

- **Backend**: FastAPI application running on `http://localhost:8000`
- **Frontend**: React application running on `http://localhost:3000`

### Development

The services are configured with hot-reload enabled, so any changes to the code will automatically restart the respective service.
