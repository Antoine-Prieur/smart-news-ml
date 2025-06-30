# Smart News ML Platform

A ML platform exploring MLOps practices. Built to explore clean abstractions, proper model lifecycle management, and scalable ML engineering patterns using Python, MongoDB, Redis, and event-driven architectures.

This platform powers [Smart News](https://smart-news-frontend.vercel.app/) and serves as a comprehensive example of how to build maintainable ML systems that can evolve and scale in production environments.

## Project Status

This is an active development project focused on platform architecture and MLOps best practices. Current priorities:

- **Platform-first approach**: Emphasizing clean interfaces and extensible design over model accuracy optimization
- **Monolithic deployment**: Models and orchestrator currently share a repository for rapid iteration - will be decomposed into microservices as the architecture matures
- **Learning-oriented**: Built to demonstrate and refine production ML engineering patterns

## 🚀 Core Features

**A/B Testing Framework**  
Deploy multiple model versions simultaneously with configurable traffic splitting and automated performance comparison.

**Extensible Model Architecture**  
Add new prediction models and content types through clean interfaces without touching core platform code.

**Complete Model Lifecycle Management**  
Version control, deployment pipelines, rollback capabilities, and automated model retirement workflows.

**Real-time Monitoring & Metrics**  
Custom performance tracking with configurable alerts and dashboard integration for production visibility.

**Event-Driven Processing**  
Asynchronous model inference and data processing using Redis pub/sub for scalable, non-blocking operations.

## 🛠️ Quick Start

**Prerequisites**

- [Poetry](https://python-poetry.org/) for dependency management
- [Docker](https://www.docker.com/) for infrastructure services
- [direnv](https://direnv.net/) (optional) for environment management

**Installation**

```bash
# Install dependencies
poetry install

# Start infrastructure services
docker-compose up -d

# Configure environment (or manually export variables from .envrc)
direnv allow
```

## 🏗️ Architecture

This platform demonstrates several key ML engineering patterns:

- **Clean separation** between model logic and platform infrastructure
- **Configuration-driven** model deployment and A/B testing
- **Event-driven** architecture for scalable async processing
- **Comprehensive monitoring** with custom metrics
- **Version-controlled** model artifacts and deployment history

## 🔗 Related Components

**[News Crawler](https://github.com/Antoine-Prieur/smart-news-crawler)**  
Rust-based content ingestion service using News API for real-time article collection and preprocessing.

**[Web API](https://github.com/Antoine-Prieur/smart-news-backend)**  
RESTful API server handling frontend integration and external service communication, built with modern Rust web frameworks.

**[Analytics Dashboard](https://github.com/Antoine-Prieur/smart-news-frontend)**  
React-based monitoring interface providing real-time insights into model performance, A/B test results, and system health metrics.
