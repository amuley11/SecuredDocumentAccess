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

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name=DynamoDBRegion)
userdata=dynamodb.Table('u_data')
client = boto3.client('ses',region_name=SESRegion)

def lambda_handler(event, context):
    

    vs_id=event['v1'].replace(' ','')
    v_code=event['v2'].replace(' ','')
    
    unacceptable_values = ['','<UserID>','UserID','<PassCode>','PassCode']

    if vs_id in unacceptable_values  or  v_code in unacceptable_values:
        return "Enter valid values for User ID against '<UserID>', Pass Code against '<PassCode>' in the address bar URL."
    
    if vs_id.isdigit() == False or v_code.isdigit() == False:
        return "Please enter a valid numeric user id and/or pass code which are shared with you over the email."
        
    # Get data from DB for the given user
    v_id = int(vs_id)
    response = userdata.get_item(Key={'u_id': v_id}, AttributesToGet=['u_code','u_name','u_email'])

    u_code=response['Item']['u_code']
    u_name=response['Item']['u_name']
    u_email=response['Item']['u_email']

    # Compare the code fetched from DB is matching with what user has provided
    if str(u_code) != str(v_code):
        print("The pass-code you provided is not matching with the system. Please provide a valid pass-code. As pass-code was not valid, de-registration process is not completed.")
        return "The pass-code you provided is not matching with the system. Please provide a valid pass-code. As pass-code was not valid, de-registration process is not completed."
    
    print("Provided pass-code is matching with the system, hence the de-registration process has started")
    
    #userdata.delete_item(Key={'u_id': v_id})
    userdata.update_item(Key={'u_id': v_id}, UpdateExpression='set u_status = :u',ExpressionAttributeValues={':u': 'de-registered'})

    SENDER = AdminEmailAddress
    RECIPIENT = u_email
    SUBJECT = "Completed - Account De-registration Request"
    BODY_TEXT = ("Dear " + u_name + ",\r\n\n"
                "As per your request, your id has been de-registered from the portal. If you want to access portal again, you'll have to complete the registration. \r\n\n"
                "Note - This is a system generated email. Please do not reply. In case of any issues, please contact your system/application administrator."
                )
    CHARSET = "UTF-8"
    
    # Send email
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
    
    return "User details have been de-activated from the portal and deregistration process is completed."