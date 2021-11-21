from app import webapp
from flask_apscheduler import APScheduler
import time
from datetime import datetime, timedelta
import re
import boto3
from ec2_metadata import ec2_metadata

scheduler = APScheduler()
scheduler.init_app(webapp)
scheduler.start()

client = boto3.client('cloudwatch')

@scheduler.task('interval', id='publish_http_metrics', seconds=60, misfire_grace_time=900)
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
        health_check = log_msg.find("ELB-HealthChecker") == -1
        if (datetime_log > (datetime.now()-one_min)):
            if health_check:
                request_in_last_min.append(log_msg)
            count+=1
        else:
            in_time = False
    client = boto3.client('cloudwatch')
    response = client.put_metric_data(
        Namespace='HTTP Request Rate',
        MetricData=[
            {
                'MetricName': 'HTTP Requests Per Minute',
                'Dimensions': [
                    {
                        'Name': 'Instance ID',
                        'Value': ec2_metadata.instance_id
                    },
                ],
                'Timestamp': datetime.now(),
                'Value': len(request_in_last_min),
                'Unit': 'Count'
            },
        ]
    )


@scheduler.task('interval', id='publish_active_status_metric', seconds=60, misfire_grace_time=900)
def publish_active_status():

    response = client.put_metric_data(
        Namespace='Worker Status',
        MetricData=[
            {
                'MetricName': 'Worker Status',
                'Dimensions': [
                    {
                        'Name': 'InstanceID',
                        'Value': ec2_metadata.instance_id
                    },
                ],
                'Timestamp': datetime.now(),
                'Value': 1,
                'Unit': 'Count'
            },
        ]
    )