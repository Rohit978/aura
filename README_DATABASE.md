# Database Setup Guide

This application uses **PostgreSQL** for production deployments and **SQLite** as a fallback for local development.

## Quick Start

### For Production (PostgreSQL)

1. **Set up PostgreSQL database** (choose one):
   - Vercel Postgres (if deploying to Vercel)
   - Supabase (free tier available)
   - Neon (free tier available)
   - Railway, Render, AWS RDS, etc.

2. **Set environment variable**:
   ```bash
   DATABASE_URL=postgresql://user:password@host:port/dbname
   ```

3. **Initialize database**:
   ```bash
   python setup_database.py
   ```

### For Local Development (SQLite)

If no PostgreSQL credentials are provided, the app automatically uses SQLite:
- Database file: `data/aura.db`
- No setup required - created automatically

## Database Schema

The database stores:

### Tables

1. **users** - User accounts
   - `user_id` (PK)
   - `email`, `name`, `password_hash`
   - `created_at`, `last_login`
   - `profile` (JSON)

2. **sessions** - Authentication sessions
   - `token` (PK)
   - `user_id` (FK)
   - `created_at`, `expires_at`

3. **songs** - Song metadata
   - `song_id` (PK)
   - `title`, `artists` (JSON), `genre` (JSON)
   - `album`, `image`, `platform`
   - `youtube_video_id`
   - `created_at`, `last_updated`

4. **user_songs** - User's song collections
   - `id` (PK)
   - `user_id` (FK), `song_id` (FK)
   - `source`, `added_at`
   - `is_favorite`, `play_count`, `last_played`

5. **listening_history** - Tracks when users listen to songs
   - `id` (PK)
   - `user_id` (FK), `song_id` (FK)
   - `song_title`, `artists` (JSON)
   - `timestamp`, `source`, `platform`
   - `duration_seconds`, `completed`
   - `metadata` (JSON)

6. **taste_profiles** - User taste profiles for recommendations
   - `id` (PK)
   - `user_id` (FK, unique)
   - `profile_data` (JSON)
   - `song_count`, `created_at`, `last_updated`

## Environment Variables

### Option 1: Full Connection String (Recommended)
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Option 2: Individual Components
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aura_music
DB_USER=postgres
DB_PASSWORD=your_password
```

**Note**: If neither `DATABASE_URL` nor `DB_PASSWORD` is set, the app uses SQLite.

## Initialization

The database is automatically initialized when:
1. The FastAPI app starts (via `@app.on_event("startup")`)
2. You run `python setup_database.py` manually
3. The Docker container starts

## Migration

Currently, the app uses SQLAlchemy's `create_all()` which creates tables if they don't exist. For production, consider using Alembic for migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Data for Model Analysis

The `listening_history` table stores all songs users listen to, which is used for:
- Taste analysis
- Recommendation generation
- User behavior tracking

Key fields for analysis:
- `song_title`, `artists` - Song identification
- `timestamp` - When they listened
- `duration_seconds` - How long they listened
- `completed` - Did they finish the song?
- `source` - Where did they find it? (recommendation, search, etc.)

## Backup and Restore

### Backup
```bash
# PostgreSQL
pg_dump -h host -U user -d dbname > backup.sql

# SQLite
cp data/aura.db data/aura.db.backup
```

### Restore
```bash
# PostgreSQL
psql -h host -U user -d dbname < backup.sql

# SQLite
cp data/aura.db.backup data/aura.db
```

## Troubleshooting

### Connection Issues

1. **Check environment variables**:
   ```bash
   echo $DATABASE_URL
   ```

2. **Test connection**:
   ```bash
   python setup_database.py
   ```

3. **Check PostgreSQL is running**:
   ```bash
   # For local PostgreSQL
   sudo systemctl status postgresql
   ```

### Table Creation Issues

If tables aren't created:
1. Check database permissions
2. Verify connection string
3. Run `setup_database.py` manually
4. Check application logs for errors

### Performance

For production:
- Add database indexes (already included in models)
- Use connection pooling (configured in `create_engine_instance()`)
- Consider read replicas for high traffic
- Regular database maintenance (VACUUM, ANALYZE)

## Security

- **Never commit** database credentials to git
- Use environment variables for all sensitive data
- Use strong passwords for production databases
- Enable SSL/TLS for database connections
- Regularly rotate database passwords
- Use least-privilege database users

