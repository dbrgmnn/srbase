# SRbase

A self-hosted Spaced Repetition System (SRS) for language learning. Built with a focus on simplicity, speed, and personal use. 

It implements the SM-2 spaced repetition algorithm, runs as a Progressive Web App (PWA), and features automated Telegram integrations.

## Features

- **Spaced Repetition (SM-2):** Automated scheduling of vocabulary reviews.
- **Progressive Web App (PWA):** Installable on iOS/Android for a full-screen mobile experience.
- **Telegram Integration:** Daily review notifications and automated database backups.
- **Zero-Build Frontend:** Pure HTML, CSS, and Vanilla JavaScript. No build steps required.

## Tech Stack

- **Backend:** Python 3.11, aiohttp, aiosqlite
- **Frontend:** Vanilla JS, HTML, CSS
- **Deployment:** Docker & Docker Compose

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/dbrgmnn/srbase.git
   cd srbase
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` as needed. `TG_TOKEN` and `TG_ADMIN` are optional and only required for Telegram notifications and backups.

3. Start the application:
   ```bash
   docker-compose up -d --build
   ```
   The application will be available at `http://localhost:8080`.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
