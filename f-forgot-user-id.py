import json
import random
import boto3
import os
from datetime import datetime
from botocore.config import Config
from decimal import Decimal

# Env variables
DynamoDBRegion=os.getenv('DynamoDBRegion')
AdminEmailAddress=os.getenv('AdminEmailAddress')
SESRegion=os.getenv('SESRegion')
APIGatewayURL=os.getenv('APIGatewayURL')
S3StaticAuth=os.getenv('S3StaticAuth')

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name=DynamoDBRegion)
userdata=dynamodb.Table('u_data')
client = boto3.client('ses',region_name=SESRegion)

def lambda_handler(event, context):
    
    # Variables passed from API
    v_email=event['v1'].strip().lower()
    
    unacceptable_values = ['','<useremailaddress>','useremailaddress']
    
    if v_email in unacceptable_values:
        return "Please enter a valid email address in the URL where it has mentioned '<UserEmailAddress>' and then submit the request. The email address entered here will be treated as a non-case-sensitive value."
    
    # Get a list of registered email addresses
    email_list=[]
    user_id=''
    #scan_res = userdata.scan(AttributesToGet=['u_seq_id','u_email','u_name'])
    scan_res = userdata.scan(AttributesToGet=['u_id','u_seq_id','u_email','u_name','u_status'])
    email_dict=scan_res['Items']
    
    # Check if user email address is available in the registered email addrersses
    for i in email_dict:
        if i['u_email'] == v_email:
            user_int_id = i['u_id']
            user_id = i['u_seq_id']
            user_name = i['u_name']
            user_status=i['u_status']
    
    # If email addresses is not registered then display the message
    if user_id == '':
        print("Your email address - " + v_email + " is not registered in the portal. Please use registration URL to proceed with the registration.")
        return "Your email address - " + v_email + " is not registered in the portal. Please use registration URL to proceed with the registration."
    
    # If email address is registered then disaply the message and send an email to the user with user id
    else:
        if user_status == 'de-registered':
            userdata.update_item(Key={'u_id': user_int_id}, UpdateExpression='set u_status = :u',ExpressionAttributeValues={':u': 'approved'})
        
        # Send email to the user
        SENDER = AdminEmailAddress
        RECIPIENT = v_email
        SUBJECT = "User ID Receovery - Secured Access Portal"
        BODY_TEXT = ("Dear " + user_name + ",\r\n\n"
                    "Your User ID is " + user_id + ". Keep it handy as you'll have to use it while logging on the portal to access documents. \r\n\n"
                    "Alternatively, you can directly go to the login scren by clicking on this URL - "+ APIGatewayURL + "?v1=" + user_id + " or you can go to " + S3StaticAuth + " to understand steps related to the process. \r\n\n\n"
                    
                    "Note - This is a system generated email. Please do not reply. In case of any issues, please contact your system/application administrator."
                    )
        CHARSET = "UTF-8"
        
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
        
        print("An email has been sent to the registered email address with details of your user id.")
        return "An email has been sent to the registered email address with details of your user id."
        