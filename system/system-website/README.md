# WordPress Website

A WordPress-based website built with Docker and Docker Compose.

## Project Structure

```
system-website/
├── wp-content/           # WordPress custom content
│   ├── plugins/         # Custom plugins
│   ├── themes/          # Custom themes
│   └── uploads/         # Uploaded media files
├── docker-compose.yml   # Docker Compose configuration
├── .gitignore          # Git ignore rules
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Setup

1. Clone the repository:
```bash
git clone <repository-url> system-website
cd system-website
```

2. Copy the environment template:
```bash
cp .env.example .env
```

3. Update `.env` with your configuration values

4. Start the services:
```bash
docker-compose up -d
```

5. Access WordPress at: `http://localhost:8080`

## Environment Variables

See `.env.example` for all available configuration options.

## Services

- **wordpress**: WordPress application (port 8080)
- **wordpress-db**: MySQL database (port 3306)

## Development

### Adding Custom Plugins

Place custom plugins in `wp-content/plugins/`

### Adding Custom Themes

Place custom themes in `wp-content/themes/`

## Deployment

Update database credentials and configurations in `.env` before deploying to production.

## License

[Specify your license here]
