from crontab import CronTab
import logging

log= logging.getLogger("config.crontab")

def cronChange(mode):

    with CronTab(tabfile='/etc/cron.d/qrCron') as cron:
        # Look for an existing job using a specific comment
        jobComment = "Job for changing guest password on rotation"
        existingJobs = cron.find_comment(jobComment)
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            job.setall(mode)
            log.info(f"Modified existing job: {job}")
            return f"Modified existing job: {job}"
        else:
            log.info(f"job not found: {existingJobs}")
            return f"job not found: {existingJobs}"
        
def getCrontab():
    try:
        file = CronTab(tabfile='/etc/cron.d/qrCron')
        return file
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An Error has occured: {e}"

def manualCron(time):
    with CronTab(tabfile='/etc/cron.d/qrCron') as cron:
        # Look for an existing job using a specific comment
        jobComment = "Job for changing guest password on rotation"
        existingJobs = cron.find_comment(jobComment)
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            job.setall(time)
            log.info(f"Modified existing job: {job}")
            return f"Cron schedule has been updated to {time}."

        else:
            log.info(f"job not found: {existingJobs}")
            return "An Error has occured. No job found. Please see logs for details"
