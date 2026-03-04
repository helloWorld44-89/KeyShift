# Cron Scheduler

Module: `app/config/crontab.py`

KeyShift manages password-rotation schedules by writing directly to a cron file at `/etc/cron.d/qrCron` using the `python-crontab` library. Each cron job is tagged with the SSID name as a comment for identification.

---

## `createCron(ssid) → str`

Creates a new cron job for the given SSID.

**Cron command:** `root cd /app/app && /usr/bin/python3 -m app.ssid {ssid.id}`

The schedule is set from `ssid.rotateFrequency` (a cron expression string).

---

## `cronChange(ssid) → str`

Updates the schedule of an existing cron job. Finds the job by comment (SSID name) and calls `job.setall(ssid.rotateFrequency)`.

---

## `deleteCron(ssid) → str`

Removes the cron job for the given SSID from the cron file.

---

## `getCrontab(comment=None) → CronJob | str`

Finds and returns the first cron job matching the given comment (SSID name). Returns an error string if not found.

---

## `manualCron(time, name) → str`

Updates the cron schedule for a job identified by `name` to the given `time` expression.

---

## Cron Expression Examples

| Expression | Meaning |
|---|---|
| `0 3 * * *` | Every day at 3:00 AM |
| `0 3 * * 1` | Every Monday at 3:00 AM |
| `0 */6 * * *` | Every 6 hours |
| `@daily` | Once per day at midnight |
