#!/bin/sh
# Seed the persistent volume if it's empty
if [ ! -f "/data/engine.db" ]; then
    echo "Seeding persistent volume with initial data..."
    cp -r ./data/* /data/ || true
fi

exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
