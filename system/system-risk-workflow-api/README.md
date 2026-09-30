# Risk Workflow API

Multi-tenant risk workflow backend service built with Node.js, Express, and MongoDB.
It provides JWT-based authentication, tenant isolation via the `x-tenant` header, and a simple workflow engine for managing risk records through their lifecycle.

## Features

- Multi-tenant API using a required `x-tenant` header on all `/api` requests
- JWT authentication (`/api/auth/login`, `/api/auth/me`)
- Risk lifecycle workflow (draft → submitted → in_review → approved/rejected → archived)
- Role-based access control with a dedicated **compliance** role for workflow actions
- Request-level IDs, structured error responses, and security best practices (`helmet`, `cors`, rate limiting)

## Tech Stack

- Node.js 20
- Express 5
- MongoDB 7 + Mongoose
- JWT (`jsonwebtoken`) for auth
- Zod for validation
- Jest + Supertest for testing
- Docker + Docker Compose for local development

## Getting Started

### Prerequisites

- Node.js 20+
- npm 10+
- MongoDB (local) or Docker
- Docker & Docker Compose (optional but recommended)

### Install Dependencies

```bash
npm install
```

### Configuration

The service is configured via environment variables. A sample file is provided:

```bash
cp .env.example .env
```

Then update `.env` as needed:

- `PORT` – API port (default: `3000`)
- `MONGO_URI` – MongoDB connection string (e.g. `mongodb://localhost:27017/risk-workflow`)
- `JWT_SECRET` – secret key used to sign JWTs

### Running the API (local)

Make sure MongoDB is running and accessible via `MONGO_URI`, then:

```bash
npm run dev
```

This starts the server with `nodemon` on `http://localhost:3000`.

For production-style runs:

```bash
npm start
```

### Running with Docker Compose

To run MongoDB and the API together:

```bash
docker-compose up --build
```

This will:

- Start a `mongo` service (MongoDB 7)
- Build and start the `api` service listening on port `3000`
- Use an internal MongoDB connection string: `mongodb://mongo:27017/risk-workflow`

You can then call the API at `http://localhost:3000`.

## Seeding a User

A helper script is provided to create users (including compliance users) in MongoDB.

```bash
node scripts/seed-user.js <email> <password> [role]
```

- `role` can be `user` or `compliance` (default: `user`)
- Requires `.env` to be configured with a valid `MONGO_URI`

Example:

```bash
node scripts/seed-user.js admin@example.com secret123 compliance
```

## API Overview

All application routes are under the `/api` prefix, and **all** of them require the `x-tenant` header.

### Health

- `GET /api/health`
  - Headers: `x-tenant: <tenant-id>`
  - Response: `{ "ok": true }`

### Authentication

Base path: `/api/auth`

- `POST /api/auth/login`
  - Headers: `Content-Type: application/json`, `x-tenant: <tenant-id>`
  - Body:
    ```json
    {
      "email": "admin@example.com",
      "password": "yourpassword"
    }
    ```
  - Response: JWT token and user info. The token is used as `Authorization: Bearer <token>`.

- `GET /api/auth/me`
  - Headers: `Authorization: Bearer <token>`, `x-tenant: <tenant-id>`
  - Response: `{ id, email, role }` for the current user.

### Risks & Workflow

Base path: `/api/risks`

High-level workflow (per tenant):

- Create a risk in `draft`
- Submit / resubmit
- Compliance assigns risk for review
- Compliance issues decision (approve/reject)
- Compliance may archive approved/rejected risks

Key endpoints (see Postman collection for complete details):

- `POST /api/risks` – create a new risk (draft)
- `GET /api/risks` – list risks
- `POST /api/risks/:id/submit` – submit draft → submitted
- `POST /api/risks/:id/resubmit` – resubmit changes_requested → submitted
- `POST /api/risks/:id/assign` – submitted → in_review (**compliance only**)
- `POST /api/risks/:id/request-changes` – in_review → changes_requested (**compliance only**)
- `POST /api/risks/:id/decision` – in_review → approved/rejected (**compliance only**, with `{"action": "approve" | "reject"}`)
- `POST /api/risks/:id/archive` – approved/rejected → archived (**compliance only**)

## Multi-Tenancy

The API is multi-tenant. Every `/api` request must include an `x-tenant` header:

```http
x-tenant: tenant-1
```

Requests are scoped by tenant, and data is isolated per tenant using middleware and Mongoose plugins.

## Testing & Linting

### Run Tests

```bash
npm test
```

Watch mode:

```bash
npm run test:watch
```

### Linting

```bash
npm run lint
npm run lint:fix
```

## API Collection (Postman)

A ready-to-use Postman collection is available at `docs/Risk-Workflow-API.postman_collection.json`.

Import it into Postman (or any compatible tool) to:

- Quickly try authentication and risk workflow endpoints
- Use collection variables for `base_url`, `tenant`, `token`, and `riskId`
- See example payloads and descriptions for each route
