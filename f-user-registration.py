import json
import random
import boto3
import os
from datetime import datetime
from botocore.config import Config
from decimal import Decimal
#from boto.dynamodb2.table import Table

# Env variables
DynamoDBRegion=os.getenv('DynamoDBRegion')
AdminEmailAddress=os.getenv('AdminEmailAddress')
SESRegion=os.getenv('SESRegion')
APIGatewayURL=os.getenv('APIGatewayURL')
MaxID=os.getenv('MaxID')
ForgotIDAPIGatewayURL=os.getenv('ForgotIDAPIGatewayURL')

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name=DynamoDBRegion)
userdata=dynamodb.Table('u_data')
client = boto3.client('ses',region_name=SESRegion)

def lambda_handler(event, context):
    
    # Variables passed from API
    #v_name=event['v1'].replace(' ','')
    v_name=event['v1'].strip()
    v_email=event['v2'].strip().lower()
    
    unacceptable_entries = ['','<username>','username','<useremailaddress>','useremailaddress']
    
    if v_name in unacceptable_entries or v_email in unacceptable_entries:
        return "Please enter a valid user name against '<UserName>' and/or email address aginst '<UserEmailAddress>' in the URL of the address bar. Email address entered here will be treated as a non-case-sensitive value."
    
    # Get a list of registered email addresses
    email_list=[]
    scan_res = userdata.scan(AttributesToGet=['u_email','u_seq_id'])
    email_dict=scan_res['Items']
    
    for i in email_dict:
        email_list.append(i['u_email'])
    #print("Resgistered emails are - " + str(email_list).strip('[]'))
    
    if v_email in email_list:
        return "Provided email address - " + v_email + " is already registered. If you have forgotten your user id associated with this email address then please click here to recover it - " + ForgotIDAPIGatewayURL + "?v1=" + v_email + "."
    
    print("Provided emails address - " + v_email + " is new. Registation process will be carried out.")
    
    # Get max id registered in a table to create the next id
    
    # Approach 1 - To generate it by incrementing the table record count by 1
    #curr_count=int(scan_res['Count'])
    #next_id=curr_count+1
    
    seq_num_list=[]
    
    for j in email_dict:
        seq_num_list.append(int(j['u_seq_id']))
        
    if seq_num_list == []:
        next_id = 1
    else:
    #Approcah 2 - Keep on generating a random number until you get one which is not in the table
        #next_id = 1
        #while next_id not in seq_num_list:
            #next_id = random.randint(1,int(MaxID))
    
    #Approcah 3 - To generate it by incrementing the key column by 1
        next_id = max(seq_num_list) + 1

    # Add record for a new user to the table with status as "pending"
    v_status='pending'
    v_code='1'
    userdata.put_item(Item={'u_id': next_id, 'u_name': v_name, 'u_email': v_email, 'u_status': v_status, 'u_seq_id': str(next_id), 'u_code': v_code})
    
    # Let admin know that there is a new user registration to be confirmed or rejected
    SENDER = AdminEmailAddress
    RECIPIENT = AdminEmailAddress
    SUBJECT = "New User Registration - Action Required"
    BODY_TEXT = ("Dear Admin, \r\n\n"
                "A new user registration has received with below details - \r\n\n"
                "User Name - " + v_name + "\r\n"
                "User Email - " + v_email + "\r\n\n"
                "To APPROVE the registration, click here - " + APIGatewayURL + "/?v1="+ str(next_id) +"&v2=approved \r\n"
                "To REJECT the registration, click here - " + APIGatewayURL + "/?v1="+ str(next_id) +"&v2=rejected \r\n\n"
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

    # Let user know that registration process has started and admin has been informed
    SENDER = AdminEmailAddress
    RECIPIENT = v_email
    SUBJECT = "Initiated - Secured Access Portal Registration"
    BODY_TEXT = ("Dear "+ v_name + ", \r\n\n"
                "Admin has been informed about your registration. You will soon hear back from us. \r\n\n\n"
                "This is a system generated email. Please don not reply back.\r\n\n"
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
    
    return 'Your registration is partially complete and subject to admin verification. Once admin takes any action - approval or rejction, you will be notified on the registered email address.'