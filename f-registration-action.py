import json
import random
import boto3
import os
from datetime import datetime
from botocore.config import Config

# Env variables
DynamoDBRegion=os.getenv('DynamoDBRegion')

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name=DynamoDBRegion)
userdata=dynamodb.Table('u_data')

def lambda_handler(event, context):
    
    # Variables passed from API
    v_id=event['v1']
    v_status=event['v2']
    
    # Update the user record in the DB table
    userdata.update_item(Key={'u_id': v_id},UpdateExpression='set u_status=:s',ExpressionAttributeValues={':s': v_status})
    
    return "User's status has been updated to " + v_status + ". An email has been triggered to the user specifying the action."
