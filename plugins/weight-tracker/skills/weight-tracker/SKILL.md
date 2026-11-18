---
name: weight-tracker
description: Use when the user reports body weight, asks to see weight history or BMI, wants the weight dashboard, or asks to correct or delete a recorded weight.
---

# Weight Tracker workflow

Use the `weight-tracker` MCP tools as the only authority for weight data. Do not edit the Excel workbook directly.

- For a new record, extract the measurement value, unit, local measurement time, timezone, and an optional note. Convert no values yourself; pass the stated unit to `record_weight`.
- Use a user-provided time when present. Otherwise, use the message time in the configured timezone and label the source as `message_time`.
- Treat `kg`, `公斤`, `千克`, `lb`, `lbs`, and `磅` as supported units. Ask for clarification if the value or unit is ambiguous.
- Report a successful write only after `record_weight` returns `created` or `already_recorded`.
- For correction or deletion, call `list_weight_records` if the target is ambiguous, then call `prepare_weight_change`. Show the returned preview and ask the user for explicit confirmation. Call `commit_weight_change` only after confirmation.
- To show trends, call `get_dashboard_url` and return the URL. The dashboard is read-only; use correction tools for edits.
- Keep replies in the user’s language. BMI is a screening metric, not medical diagnosis.
