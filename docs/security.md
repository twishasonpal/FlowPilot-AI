# Security notes

- The tool registry contains fixed tool identifiers; request data cannot select arbitrary code.
- The local approval endpoint verifies a hash of the exact payload and rejects replay.
- File names are reduced to basenames; uploads are limited to text/Markdown and size bounded.
- No live outbound REST, SMTP, or n8n connector is enabled in this build.
- The local development API has no authentication. Do not expose it to an untrusted network or use it for real customer data.
- Configure a strong `SECRET_KEY`, real authentication/authorization, HTTPS, secret storage, migrations, and outbound SSRF controls before deployment.
