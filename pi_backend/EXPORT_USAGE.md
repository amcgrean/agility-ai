# Training Export Usage

Use the helper script on the Pi so you do not need to look up the export token manually.

Default export command:

```bash
python3 ~/agility-ai/export_training_dataset.py
```

Write to a custom file:

```bash
python3 ~/agility-ai/export_training_dataset.py ~/agility-ai/exports/training-export-$(date +%F).json
```

Notes:
- The script reads `ADMIN_EXPORT_TOKEN` from `~/agility-ai/.env`
- It calls `http://127.0.0.1:8000/admin/training-export`
- It exports only conversations where training consent is enabled
- Exported records are redacted and user-hashed by the backend
