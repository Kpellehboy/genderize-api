# Genderize Proxy API

A FastAPI proxy that enriches Genderize.io responses with confidence scoring and ISO timestamps.

## Base URL
`http://localhost:8000/api/classify?name=john`

## Endpoint
`GET /api/classify?name={name}`

## Example Response
<img width="818" height="510" alt="image" src="https://github.com/user-attachments/assets/e45248e0-306f-42f8-a03b-f78c111d1109" />


## Local Development
<img width="1100" height="281" alt="image" src="https://github.com/user-attachments/assets/526c1041-ff1a-42a3-8791-ca3130621d8b" />


## Deployment
Deployed on Render. Automatic deploys from main branch.

## Assumptions & Edge Cases
- Non-string `name` in query params is impossible (HTTP query strings are always strings), but code includes a check for completeness.
- When Genderize returns `gender: null` or `count: 0`, returns 404 with error message.
- Confidence requires BOTH probability >= 0.7 AND sample_size >= 100.

## Potential Improvements
- Add Redis caching to reduce external API calls.
- Add rate limiting per IP.
- Add request ID for tracing.
