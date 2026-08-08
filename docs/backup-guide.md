# ABS ERP — Database Backup & Disaster Recovery Guide

Because ABS ERP manages core organizational finances, invoices, payments, and customer records, routine database backup and restoration procedures are mandatory.

---

## 1. PostgreSQL Production Backup (`pg_dump`)

### Daily Automated Backup Command
To take an encrypted, compressed database dump:

```bash
pg_dump -U <db_user> -h <db_host> -p <db_port> -F c -b -v -f "abs_erp_backup_$(date +%Y%m%d_%H%M%S).dump" <db_name>
```

### PostgreSQL Restoration Command (`pg_restore`)
To restore a backup into a fresh or recovered database instance:

```bash
pg_restore -U <db_user> -h <db_host> -p <db_port> -d <db_name> -v "abs_erp_backup_20260808_120000.dump"
```

---

## 2. SQLite Development Snapshot Backup

For local testing or staging environments using SQLite:

### Backup Command (Windows PowerShell)
```powershell
Copy-Item db.sqlite3 -Destination "backups\db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sqlite3"
```

### Backup Command (Linux/macOS)
```bash
cp db.sqlite3 backups/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3
```

---

## 3. Media & Generated Document Storage Backup

Generated PDF receipts, statements, and uploaded files located in `media/` must be backed up alongside database snapshots:

```bash
tar -czvf "media_backup_$(date +%Y%m%d).tar.gz" media/
```
