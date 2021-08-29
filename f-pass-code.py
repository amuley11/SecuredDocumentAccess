import json
import random
import boto3
import os
from botocore.config import Config

# Env variables
AdminEmailAddress = os.getenv('AdminEmailAddress')
SESRegion = os.getenv('SESRegion')
APIGatewayURL = os.getenv('APIGatewayURL')
APIGatewayAdminURL = os.getenv('APIGatewayAdminURL')
S3Bucket=os.getenv('S3Bucket')
S3Region=os.getenv('S3Region')
S3Folder=os.getenv('S3Folder')
S3_config = Config(
    region_name = S3Region,
    signature_version = 's3v4',
    s3={'addressing_style': 'path'},
)
s3_client = boto3.client('s3', config=S3_config)

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
userdata = dynamodb.Table('u_data')
client = boto3.client('ses',region_name=SESRegion)
BucketObjects=[]
    
def lambda_handler(event, context):
    # Variables passed from API
    vs_id=event['v1'].replace(' ','')
    
    unacceptable_values = ['','<UserID>','UserID','<PassCode>','PassCode','<DocName>','DocName']
    
    if vs_id in unacceptable_values:
        return "Enter valid values for User ID against '<UserID>' in the address bar URL."
    
    if vs_id.isdigit() == False:
        return "Please enter a valid numeric user id which is shared with you over the email."
    
    # Fetch recepient's email address & name from DB
    v_id = int(vs_id)
    response = userdata.get_item(Key={'u_id': v_id},AttributesToGet=['u_email','u_name','u_status'])
    
    # If user is not registered then end the process by sending a message
    if len(response) == 1:
        return ("User ID you entered is not registered. Please provide a valid User ID.")
        
    # As user is registered, get his/her attributes
    item = response['Item']
    u_email = item["u_email"]
    u_name = item["u_name"]
    u_status = item["u_status"]
    
    # If user is registered then check whether he/she is active
    
    if u_status == 'rejected':
        return "Admin has rejected your request. Please contact administrator for next action."
    
    if u_status == 'pending':
        return "Admin has been informed about your registration. If your request is not approved within 2 hour then please contact the administrator."
    
    if u_status == 'de-registered':
        
        new_status = 'pending'
        userdata.update_item(Key={'u_id': v_id},UpdateExpression='set u_status=:s',ExpressionAttributeValues={':s': new_status})
        
        # Let admin know that there is a returning user registration to be confirmed or rejected
        SENDER = AdminEmailAddress
        RECIPIENT = AdminEmailAddress
        SUBJECT = "Returning User Registration - Action Required"
        BODY_TEXT = ("Dear Admin, \r\n\n"
                    "A returning user registration has received with below details - \r\n\n"
                    "User Name - " + u_name + "\r\n"
                    "User Email - " + u_email + "\r\n\n"
                    "To APPROVE the registration, click here - " + APIGatewayAdminURL + "/?v1="+ vs_id +"&v2=approved \r\n"
                    "To REJECT the registration, click here - " + APIGatewayAdminURL + "/?v1="+ vs_id +"&v2=rejected \r\n\n"
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

        return "Admin has been informed that you are trying to re-login post de-registration from the portal. Admin will take the necessary action to approve/reject your request. If you don't hear back within next 2 hours, please contact administrator."
    
    # If user is active then proceed with next steps to generate a pass-code and it via email
    
    # Generate a random code
    code = str(random.randint(100000,999999))
    print("code ="+code)
    
    # Update the pass-code into the table
    userdata.update_item(Key={'u_id': v_id},UpdateExpression='set u_code=:u',ExpressionAttributeValues={':u': code})
    
    # To list the objects available in the bucket
    for bucket_objects in s3_client.list_objects_v2(Bucket=S3Bucket) ['Contents']:
        if bucket_objects['Key'][-1] != '/':
            BucketObjects.append(bucket_objects['Key'])
    
    EgFile=BucketObjects[0]
    BucketObejctList = str(BucketObjects).strip('[]')
    
    # Prepare the email content
    SENDER = AdminEmailAddress
    RECIPIENT = u_email
    SUBJECT = "Your temporary pass-code for accesing the file"
    BODY_TEXT = ("Dear " + u_name + ",\r\n\n"
                "Your temporary pass-code for this operation is " + code + ".\r\n\n"
                "Your ONE-time URL to access the portal is partially created. You just have to enter a file name which you want to access. Here is your URL - \r\n"
                + APIGatewayURL + "/?v1=" + str(v_id) + "&v2=" + code + "&v3=<<put file name here>> \r\n\n"
                "e.g. The first file from the list can be asscess using this URL - " + APIGatewayURL + "/?v1=" + str(v_id) + "&v2=" + code + "&v3=" + EgFile + ".\r \n\n"
                "Here are the files available inside the bucket. Please use them without quotes in your next request - \r \n"
                + BucketObejctList + "\r \n\n\n"
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
    
    BucketObjects.clear()
    return ('An email with a temporary pass-code has been sent to your registered email address. Please follow the instructions given in the email, to access the required document. While providing the document name in the next request, please do not use the quotes provided with their names in the email.')
