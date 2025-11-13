# Whales Market Monitor

**Real-time monitor for Whales.Market pre-market tokens with Telegram alerts**

---

## Overview

This project monitors pre-market buy/sell offers for tokens listed on [Whales.Market](https://whales.market) and sends Telegram alerts when notable changes occur. It focuses on reliability, safe handling of credentials, and easy deployment.

## Features

- Polls Whales.Market API for `pre_market` orders (buy/sell).
- Parses special price formats (e.g. `0.0₃78`).
- Detects meaningful changes and sends formatted Telegram alerts.
- Logs to file and stdout for debugging.
- Config-driven: tokens, chains, and Telegram credentials are stored in `config.py` (kept out of source control).

## Security & Privacy

**Never** commit `config.py` containing real API keys or tokens. This repository includes `config.example.py` with placeholders — copy it to `config.py` and populate your secrets locally.

## Quickstart (Linux / macOS)

1. Clone the repo:

   ```bash
   git clone <repo-url>
   cd whales-monitor
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create `config.py` from the example:

   ```bash
   cp config.example.py config.py
   # Edit config.py and add your BOT_TOKEN, CHAT_ID and TOKENS mapping
   ```

4. Run the monitor:

   ```bash
   python whales_monitor.py
   ```

## Docker (optional)

A `Dockerfile` is included to build a lightweight container. Build and run:

```bash
docker build -t whales-monitor .
docker run --env-file .env --rm whales-monitor
```

> Use an `.env` or Docker secrets; do not bake tokens into the image or commit them.

## Project Structure

```
whales-monitor/
├─ whales_monitor.py        # Main monitoring program
├─ config.example.py        # Example config with placeholders
├─ requirements.txt
├─ LICENSE
├─ .gitignore
└─ README.md
```

## Contributing

Contributions are welcome. Open issues and PRs for improvements such as:
- Improved error handling and retries
- Metrics/telemetry (Prometheus)
- Unit tests and CI
- Support for additional order types or exchanges

## License

This project is released under the MIT License. See `LICENSE` for details.
