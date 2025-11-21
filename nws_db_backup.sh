#!/bin/bash
#
# PostgreSQL Docker backup script
# Creates timestamped .dump files from a running postgres container
#

# === Configuration ===
CONTAINER_NAME="postgres-db"             # name of your running container
DB_NAME="nwshistory"                        # database to back up
DB_USER="nws"                      # database user
BACKUP_DIR="/home/jolhid/nws/backups/postgres"    # host directory for backups


# === Derived values ===
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
FILENAME="${DB_NAME}-${TIMESTAMP}.dump"
TMP_PATH="/tmp/${FILENAME}"

# === Ensure backup directory exists ===
mkdir -p "${BACKUP_DIR}"

echo "Backing up database '${DB_NAME}' from container '${CONTAINER_NAME}'..."
echo "Output file: ${BACKUP_DIR}/${FILENAME}"

# === Run pg_dump inside the container ===
docker exec -t "${CONTAINER_NAME}" \
    pg_dump -U "${DB_USER}" -F c -b -v -f "${TMP_PATH}" "${DB_NAME}"

# === Copy backup file to host ===
docker cp "${CONTAINER_NAME}:${TMP_PATH}" "${BACKUP_DIR}/${FILENAME}"

# === Clean up temp file inside container ===
docker exec "${CONTAINER_NAME}" rm -f "${TMP_PATH}"

# === (Optional) compress the backup ===
gzip -9 "${BACKUP_DIR}/${FILENAME}"

echo "Backup complete: ${BACKUP_DIR}/${FILENAME}.gz"

