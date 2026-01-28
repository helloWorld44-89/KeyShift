from crontab import CronTab

def cronChange(mode):

    with CronTab(tabfile='/etc/cron.d/qrCron') as cron:
        # Look for an existing job using a specific comment
        jobComment = "Job for changing guest password on rotation"
        existingJobs = cron.find_comment(jobComment)
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            job.setall(mode)

            return f"Modified existing job: {job}"
        else:
            
            return f"job not found: {existingJobs}"
        
def getCrontab():
    file = CronTab(tabfile='/etc/cron.d/qrCron')
    return file

def manualCron(time):
    with CronTab(tabfile='/etc/cron.d/qrCron') as cron:
        # Look for an existing job using a specific comment
        jobComment = "Job for changing guest password on rotation"
        existingJobs = cron.find_comment(jobComment)
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            job.setall(time)
            return f"Cron schedule has been updated to {time}."

        else:
            return "An Error has occured. No job found. Please see logs for details"
