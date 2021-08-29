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

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name=DynamoDBRegion)
userdata=dynamodb.Table('u_data')
client = boto3.client('ses',region_name=SESRegion)

def lambda_handler(event, context):
    
    # Variables passed from API
    vs_id=event['v1'].replace(' ','')
    
    unacceptable_values = ['','<UserID>','UserID','<PassCode>','PassCode','<DocName>','DocName']
    
    if vs_id in unacceptable_values:
        return "Enter valid values for User ID against '<UserID>' in the address bar URL."
    
    if vs_id.isdigit() == False:
        return "Please enter a valid numeric user id which is shared with you over the email."
    
    v_id = int(vs_id)
    
    # Get a list of registered user IDs
    user_id_list=[]
    
    scan_res = userdata.scan(AttributesToGet=['u_seq_id'])
    user_id_dict=scan_res['Items']
    
    for i in user_id_dict:
        user_id_list.append(i['u_seq_id'])
    
    if vs_id in user_id_list:
        response = userdata.get_item(Key={'u_id': v_id}, AttributesToGet=['u_code','u_name','u_email'])

        u_code=response['Item']['u_code']
        u_name=response['Item']['u_name']
        u_email=response['Item']['u_email']
    
        SENDER = AdminEmailAddress
        RECIPIENT = u_email
        SUBJECT = "Initiated - Account De-registration Request"
        BODY_TEXT = ("Dear " + u_name + ",\r\n\n"
                    "Request to de-register your account has been received. If it was not raised by you or raised by an accident then no action is required from your side. \r\n\n"
                    "If request is valid then click the below URL and your account detais will be removed from the portal. Please note than once you click the URL, your action can not be rolled back. - \r\n\n"
                    " To de-register - " + APIGatewayURL + "?v1=" + vs_id + "&v2=" + u_code + ". \r\n\n\n"
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
    
        return "Email for de-registering the the account from Secured Access portal, has been sent to your registered email address. Please follow the steps provided in the email to complete the de-registration."
    else:
        return "Entered user id - " + vs_id + " is not registered with the portal. Please enter a correct user id."