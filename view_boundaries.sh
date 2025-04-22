#!/bin/bash

# Set the database file path
DB_FILE="users.db"

# Check if the database file exists
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Error: Database file '$DB_FILE' not found!"
    exit 1
fi

# Run SQLite command to view the `boundaries` table
echo "📐 Fetching boundaries from database..."
sqlite3 "$DB_FILE" <<EOF
.headers on
.mode column
SELECT * FROM boundaries;
EOF
