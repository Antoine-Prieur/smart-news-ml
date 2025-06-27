# Smart News ML Platform

An ML platform built to explore and demonstrate production-quality patterns in Python, MongoDB, Redis, and modern ML practices.

This project powers [Smart News](https://smart-news-frontend.vercel.app/) and represents my attempt to build the kind of ML engineering environment I'm passionate about - one with clean abstractions, proper model lifecycle management, and thoughtful architecture. It's my playground for implementing the MLOps practices I believe make ML systems maintainable and scalable.

## 🚀 Features

- A/B Testing: Traffic distribution and model comparison framework
- Extensible Design: Easy addition of new model versions and prediction types through clean interfaces
- Model Versioning: Complete predictor lifecycle management
- Metrics & Monitoring: Real-time performance tracking with custom metrics
- Event-Driven Architecture: Asynchronous processing with redis

## 🛠️ Installation

This project uses [Poetry](https://python-poetry.org/) to manage requirements.

```bash
poetry install
```

I also use [direnv](https://direnv.net/) to setup environment, but you can just skip it and export variables in `.envrc`.

To setup dependencies:

```bash
docker-compose up -d
```

## 🔗 Related Projects

- [News Crawler](https://github.com/Antoine-Prieur/smart-news-crawler): Rust-based news scraping using News API (Note: Used this project to learn Rust)
- [Web API](https://github.com/Antoine-Prieur/smart-news-backend): RESTful API server for frontend integration (Also part of my Rust learning journey)
- [Dashboard](https://github.com/Antoine-Prieur/smart-news-frontend): React-based analytics and monitoring interface (Built using a template with lots of vibe coding - frontend wasn't the focus here)
