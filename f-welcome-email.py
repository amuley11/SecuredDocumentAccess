import json
import random
import boto3
import os
from botocore.config import Config

# Env variables
AdminEmailAddress = os.getenv('AdminEmailAddress')
SESRegion = os.getenv('SESRegion')
APIGatewayURL=os.getenv('APIGatewayURL')
S3StaticAuth=os.getenv('S3StaticAuth')

# Resources to be used
client = boto3.client('ses',region_name=SESRegion)

def lambda_handler(event, context):
    for record in event['Records']:
        print(record)
        # Setting up the variable values
        
        if record['eventName'] == 'REMOVE':
            return "Exiting the process as REMOVE event occured which is not required for this process."
        
        if record['eventName'] == 'MODIFY':
            oldImage = record['dynamodb']['OldImage']
            u_oldid = oldImage['u_id']['N']
            u_oldemail = oldImage['u_email']['S']
            u_oldname = oldImage['u_name']['S']
            u_oldstatus = oldImage['u_status']['S']
            
        newImage = record['dynamodb']['NewImage']
        u_newid = newImage['u_id']['N']
        u_newemail = newImage['u_email']['S']
        u_newname = newImage['u_name']['S']
        u_newstatus = newImage['u_status']['S']

        if ((record['eventName'] == 'INSERT' and u_newstatus =='approved') or (record['eventName'] == 'MODIFY' and (u_newstatus =='approved' or u_newstatus =='rejected') and u_oldstatus == 'pending')):
            # Prepare the email content
            SENDER = AdminEmailAddress
            RECIPIENT = u_newemail
            
            if u_newstatus =='approved':
                SUBJECT = "Approved - Secured Access Portal Registration"
                BODY_TEXT = ("Dear " + u_newname + ",\r\n\n"
                    "Your registration on the Secured Access portal (http://securedaccess.borrowedcloud.com) has been successfully completed! Your User ID is " + u_newid + ". Keep it handy as you'll have to use it while logging on the portal to access documents. \r\n\n"
                    "Alternatively, you can directly go to the login scren by clicking on this URL - "+ APIGatewayURL + "?v1=" + u_newid + " or you can go to " + S3StaticAuth + " to understand steps related to the process. \r\n\n\n"
                    
                    "Note - This is a system generated email. Please do not reply. In case of any issues, please contact your system/application administrator."
                    )
            else:
                SUBJECT = "Rejected - Secured Access Portal Registration"
                BODY_TEXT = ("Dear " + u_newname + ",\r\n\n"
                    "Your registration could not be completed. Please contact system administrator. \r\n\n"
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
            msg="Email related to the registration was sent successfully to the user."
            print(msg)
        else:
            msg="Required event didn't occur, so email wasn't sent"
            print(msg)
    return msg
