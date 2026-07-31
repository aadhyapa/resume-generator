# resume-generator

## Backend generate-resume protection

`POST /generate_resume` is guarded because it can spend external AI API credits. Set at least one API key before running or deploying the backend:

```bash
export GENERATE_RESUME_API_KEYS="replace-with-a-long-random-secret"
```

Clients can authenticate with either header format:

```http
X-API-Key: replace-with-a-long-random-secret
```

or:

```http
Authorization: Bearer replace-with-a-long-random-secret
```

Optional guardrail settings:

| Environment variable | Default | Purpose |
| --- | ---: | --- |
| `GENERATE_RESUME_API_KEYS` | none | Comma-separated list of valid API keys. If unset, `/generate_resume` fails closed with `503`. |
| `GENERATE_RESUME_RATE_LIMIT_REQUESTS` | `10` | Maximum authenticated generate requests per key/IP identity. |
| `GENERATE_RESUME_RATE_LIMIT_WINDOW_SECONDS` | `3600` | Sliding-window duration for the in-memory rate limit. |
| `GENERATE_RESUME_MAX_JOB_DESCRIPTION_CHARS` | `12000` | Maximum accepted job-description length before AI providers are called. |

The current limiter is intentionally isolated behind `InMemoryRateLimiter` in `backend/security.py` so it can be replaced with Redis or another shared store when the backend runs with multiple workers or instances.
