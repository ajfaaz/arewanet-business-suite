# ABS ERP — Production Readiness Checklist

This document details the security, database, file handling, email, and monitoring checklist required before deploying ABS ERP to a production environment.

---

## 1. Security Checklist

- [ ] **`DEBUG = False`**: Ensure `DEBUG=False` in production environment settings.
- [ ] **Strong `SECRET_KEY`**: Set a cryptographically secure, random 64-character secret key.
- [ ] **HTTPS / TLS Enforcement**:
  - `SECURE_SSL_REDIRECT = True`
  - `SESSION_COOKIE_SECURE = True`
  - `CSRF_COOKIE_SECURE = True`
  - `SECURE_HSTS_SECONDS = 31536000`
- [ ] **CORS Configuration**: Restrict `CORS_ALLOWED_ORIGINS` strictly to authorized web and mobile app domains.
- [ ] **JWT Configuration**:
  - Review access token expiration (`JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60`).
  - Enable token blacklisting on logout.
- [ ] **Allowed Hosts**: Explicitly configure `ALLOWED_HOSTS` with server domains/IPs.

---

## 2. Database Checklist

- [ ] **Production RDBMS**: Deploy PostgreSQL 14+ for production environments.
- [ ] **Database Connection Pooling**: Configure PgBouncer or Django persistent database connections (`CONN_MAX_AGE`).
- [ ] **Composite Indexes Verified**: Ensure migrations containing composite indexes (`organization + status`, `organization + invoice_date`, `organization + due_date`) are applied.
- [ ] **Automated Backups**: Configure daily automated database backups with off-site replication.

---

## 3. Static & Media Files Checklist

- [ ] **Static File Collection**: Run `python manage.py collectstatic --noinput` during deployment pipeline.
- [ ] **Storage Backend**: Configure AWS S3, DigitalOcean Spaces, or Nginx media root for PDF generation and document uploads.
- [ ] **Media Backup Strategy**: Backup document attachments and generated receipts/invoices daily.

---

## 4. Email & SMTP Delivery Checklist

- [ ] **Production Mail Relay**: Configure transactional email provider (SendGrid, Mailgun, Amazon SES).
- [ ] **Authentication Protocols**: Ensure domain has valid **SPF**, **DKIM**, and **DMARC** records for reliable invoice delivery.

---

## 5. Monitoring & Operational Logging

- [ ] **Application Logs**: Configure log rotation (`RotatingFileHandler` / Sentry / Datadog).
- [ ] **Error Tracking**: Integrate exception monitoring (e.g. Sentry) to capture unexpected 500 errors.
- [ ] **Uptime & Health Checks**: Ping `GET /api/v1/health/` every 60 seconds from load balancer / uptime service.
