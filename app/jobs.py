from app import webapp
from flask_apscheduler import APScheduler
import time
from datetime import datetime, timedelta
import re
import boto3


scheduler = APScheduler()
scheduler.init_app(webapp)
scheduler.start()



@scheduler.task('interval', id='publish_http_metrics', seconds=5, misfire_grace_time=900)
def publish_http_request_rate():
    with open('access.log') as f:
        lines = f.readlines()
    in_time = True
    count = 1
    request_in_last_min = []
    while(in_time):
        log_msg = lines[len(lines)-count]
        first = log_msg.find("[")
        second = log_msg.find("]")
        log_time = log_msg[first+1:second-6]
        datetime_log = datetime.strptime(log_time, '%d/%b/%Y:%H:%M:%S')
        one_min = timedelta(minutes=1)
       # print(log_msg)
        health_check = log_msg.find("ELB-HealthChecker") == -1
       # print(log_msg.find("ELB-HealthChecker"))
        if (datetime_log > (datetime.now()-one_min)):
            if health_check:
                request_in_last_min.append(log_msg)
            count+=1
        else:
            in_time = False
    print(len(request_in_last_min))


