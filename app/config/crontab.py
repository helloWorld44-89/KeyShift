from crontab import CronTab
import logging
from ..models import SSID

log = logging.getLogger("config.crontab")

# Path to the cron file managed by KeyShift inside the container
filePath = '/etc/cron.d/qrCron'
# For local development, use the line below instead:
# filePath = './app/crontab'


def cronChange(ssid: SSID) -> str:
    """
    Update the cron schedule for an existing rotation job.

    Finds the job by its comment (the SSID name) and updates its schedule
    to the value stored in ssid.rotateFrequency.

    Args:
        ssid: The SSID whose rotation schedule should be updated.

    Returns:
        A status message string.
    """
    try:
        with CronTab(tabfile=filePath) as cron:
            jobComment = ssid.ssidName
            existingJobs = list(cron.find_comment(jobComment))
            if existingJobs:
                job = existingJobs[0]
                job.setall(ssid.rotateFrequency)  # Apply new cron schedule
                log.info(f"Modified existing job: {job}")
                log.debug(f"Existing job {job} | {ssid}")
                return f"Modified existing job: {job}"
            else:
                log.error(f"job not found: {existingJobs}")
                return f"job not found: {existingJobs}"
    except Exception as e:
        log.error({e} | {existingJobs})


def getCrontab(comment: str = None):
    """
    Retrieve the cron job for a given SSID by its comment tag.

    Args:
        comment: The SSID name used as the cron job comment.

    Returns:
        The CronJob object if found, or an error string.
    """
    try:
        with CronTab(tabfile=filePath) as cron:
            existingJobs = list(cron.find_comment(comment))
            if existingJobs:
                job = existingJobs[0]
                log.info(f"Found existing job: {job}")
                return job
            else:
                log.info(f"No existing job found with comment: {comment}")
                return f"No existing job found for SSID: {comment}"
    except Exception as e:
        log.error({e})
        return f"An Error has occured: {e}"


def manualCron(time: str, name: str) -> str:
    """
    Set a custom cron schedule for a job identified by SSID name.

    Called from the admin UI when a user manually overrides the schedule.

    Args:
        time: New cron expression (e.g. '0 3 * * 1').
        name: SSID name (used as the job comment to locate it).

    Returns:
        A confirmation or error message string.
    """
    with CronTab(tabfile=filePath) as cron:
        jobComment = name
        existingJobs = list(cron.find_comment(jobComment))
        if existingJobs:
            job = list(existingJobs)[0]
            job.setall(time)
            log.info(f"Modified existing job: {job}")
            return f"Cron schedule has been updated to {time}."
        else:
            log.error(f"job not found: {existingJobs}")
            return "An Error has occured. No job found. Please see logs for details"


def createCron(ssid: SSID) -> str:
    """
    Create a new cron job for scheduled password rotation.

    The cron command runs app/ssid.py with the SSID's database ID so the
    correct SSID is targeted at rotation time.

    Args:
        ssid: The SSID to create the rotation schedule for.

    Returns:
        A confirmation or error message string.
    """
    try:
        with CronTab(tabfile=filePath) as cron:
            # Command runs the per-SSID rotation script inside the container
            job = cron.new(
                command=f'root cd /app/app && /usr/bin/python3 -m app.ssid {ssid.id}',
                comment=ssid.ssidName  # Tag with SSID name for later identification
            )
            job.setall(ssid.rotateFrequency)
            cron.write()
            log.info(f"Created new cron job: {job}")
            log.debug(f"Created new Job: {job} | SSID: {ssid}")
            return f"Created new cron job: {job}"
    except Exception as e:
        log.error(e)
        return f"An Error has occured: {e}"


def deleteCron(ssid: SSID) -> str:
    """
    Remove the rotation cron job for the given SSID.

    Args:
        ssid: The SSID whose cron job should be deleted.

    Returns:
        A confirmation or error message string.
    """
    try:
        with CronTab(tabfile=filePath) as cron:
            existingJobs = cron.find_comment(ssid.ssidName)
            if existingJobs:
                job = list(existingJobs)[0]
                cron.remove(job)
                cron.write()
                log.info(f"Deleted cron job: {job}")
                return f"Deleted cron job: {job}"
            else:
                log.info(f"No existing job found with comment: {ssid.ssidName}")
                return f"No existing job found for SSID: {ssid.ssidName}"
    except Exception as e:
        log.error(e)
        return f"An Error has occured: {e}"
