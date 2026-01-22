from crontab import CronTab

def cronChange(time,interval=0, mode='daily'):

    with CronTab(user='root') as cron:
        # Look for an existing job using a specific comment
        jobComment = "Job for changing guest password on rotation"
        existingJobs = cron.find_comment(jobComment)
        splitTime = time.split(':')
        if existingJobs:
            # Edit the existing job        
            job = list(existingJobs)[0] # Get the first job found
            match mode:
                case mode if mode == 'daily':
                    job.setall(splitTime[1],splitTime[0],f'*/{interval}')
                case mode if mode == 'weekly':
                    job.setall(splitTime[1],splitTime[0],0,f'*/{interval}')
                case mode if mode == 'monthly':
                    job.setall(splitTime[1],splitTime[0],0,0,f'*/{interval}')

            return f"Modified existing job: {job}"
        else:
            
            return f"job not found: {existingJobs}"
        
def getCrontab():
    file = CronTab(user='root')
    return file