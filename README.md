# Crypto Exchange Project

This repository contains the source code for a project that interfaces with a cryptocurrency exchange. The project demonstrates the use of various DevOps tools and distributed systems paradigms, such as Docker, Kafka, Redis, and FastAPI.

**Disclaimer:** This project is for educational and informational purposes only. Users are responsible for their actions and any consequences that may arise from using the software. Consult with legal counsel if you have concerns about potential liability.

## Features

### Completed Features

- Real-time data streaming using Kafka
- Caching using Redis
- API built with FastAPI
- Containerization with Docker
- Asynchronous task handling with asyncio

### In Progress / Planned Features

- Unit and integration tests
- Enhanced error handling and logging
- Additional API endpoints
- Improved monitoring and alerting

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Setup and Running the Project

1. Clone the repository:

```bash
git clone https://github.com/lfang615/bybit-service.git
```

2. Change to the project directory:

```bash
cd crypto-exchange-project
```

3. Run the project using Docker Compose:

```bash
docker-compose up
```

## Usage

The API has the following endpoints:

- `GET /orders`: Retrieve orders from the cache
- `GET /positions`: Retrieve positions from the cache

The frontend component can be accessed by visiting `http://localhost:8000` in your web browser.

## Contributing

Contributions are welcome! If you're interested in contributing to this project, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).