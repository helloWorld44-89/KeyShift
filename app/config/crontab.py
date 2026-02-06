from crontab import CronTab
import logging
from ..models import SSID

log= logging.getLogger("config.crontab")
#filePath = '/etc/cron.d/qrCron'
filePath = './app/crontab'
def cronChange(ssid:SSID):

    with CronTab(tabfile=filePath) as cron:
        # Look for an existing job using a specific comment
        jobComment = ssid.ssidName
        existingJobs = cron.find_comment(jobComment)
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            job.setall(ssid.rotateFrequency)
            log.info(f"Modified existing job: {job}")
            log.debug(f" Exisiting job {job} | {ssid}")
            return f"Modified existing job: {job}"
        else:
            log.error(f"job not found: {existingJobs}")
            return f"job not found: {existingJobs}"
        
def getCrontab():
    try:
        file = CronTab(tabfile=filePath)
        return file
    except Exception as e:
        log.error({e})
        return f"An Error has occured: {e}"

def manualCron(time):
    with CronTab(tabfile=filePath) as cron:
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
            log.error(f"job not found: {existingJobs}")
            return "An Error has occured. No job found. Please see logs for details"

def createCron(ssid:SSID):
    try:
        with CronTab(tabfile=filePath) as cron:
            job = cron.new(command=f'root /usr/bin/python3 /app/app/config/rotatePW.py {ssid.id}', comment=ssid.ssidName)
            job.setall(ssid.rotateFrequency)
            cron.write()
            log.info(f"Created new cron job: {job}")
            log.debug(f"Created new Job: {job} | SSID: {ssid}")
            return f"Created new cron job: {job}"
    except Exception as e:
        log.error(e)
        return f"An Error has occured: {e}"


