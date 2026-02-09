#!/usr/bin/env python3
import boto3
from datetime import datetime

client = boto3.client('logs', region_name='ca-west-1')
log_group = '/aws/lambda/compliance-platform-api'

try:
    # Get the latest log stream
    streams = client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    
    if not streams['logStreams']:
        print("No log streams found")
        exit(1)
    
    stream_name = streams['logStreams'][0]['logStreamName']
    print(f"Latest log stream: {stream_name}\n")
    print("=" * 80)
    
    # Get the latest events
    events = client.get_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        limit=100
    )
    
    # Print the last 30 events
    for event in events['events'][-30:]:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        print(f"[{timestamp}] {event['message']}")
    
except Exception as e:
    print(f"Error: {e}")
