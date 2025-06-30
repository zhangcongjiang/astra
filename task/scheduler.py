from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from django_apscheduler import util

scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")

@util.close_old_connections
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("APScheduler started successfully!")

def get_scheduler():
    return scheduler