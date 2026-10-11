# eShopCo latency API — from scratch

Uses the supplied telemetry JSON and a Vercel Python function.

## Project files
- `api/index.py`: endpoint and metric calculations
- `data/telemetry.json`: sample telemetry data
- `vercel.json`: Vercel function configuration and data-file bundling

## Deploy
1. Create a GitHub repository and upload the contents of this folder, preserving `api/` and `data/`.
2. Import the repository at https://vercel.com/new.
3. Deploy. Your POST endpoint will be `https://YOUR-DEPLOYMENT-DOMAIN/api`.

## PowerShell POST test
```powershell
$url = "https://YOUR-DEPLOYMENT-DOMAIN/api"
$body = @{
    regions = @("amer", "apac")
    threshold_ms = 171
} | ConvertTo-Json

Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json" -Body $body
```

## CORS preflight test
```powershell
$url = "https://YOUR-DEPLOYMENT-DOMAIN/api"
$r = Invoke-WebRequest -Uri $url -Method OPTIONS -Headers @{
    Origin = "https://example.com"
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "content-type"
}
$r.StatusCode
$r.Headers
```

Expected headers include `Access-Control-Allow-Origin: *`,
`Access-Control-Allow-Methods: POST, OPTIONS`, and
`Access-Control-Allow-Headers: Content-Type`.

## Metrics
- `avg_latency`: arithmetic mean of regional `latency_ms`.
- `p95_latency`: linearly interpolated 95th percentile.
- `avg_uptime`: arithmetic mean of regional `uptime_pct`.
- `breaches`: count of records with latency strictly greater than `threshold_ms`.

The endpoint supports POST, OPTIONS, and GET health checks. CORS headers are added to JSON responses and OPTIONS preflight responses.
