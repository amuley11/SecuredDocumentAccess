import json
import random
import boto3
import os
from datetime import datetime
from botocore.config import Config
from boto3 import client

# Env variables
ExpiresInSec=os.getenv('ExpiresInSec')
S3Bucket=os.getenv('S3Bucket')
S3Region=os.getenv('S3Region')
S3Folder=os.getenv('S3Folder')

# Define resources to be used
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
userdata=dynamodb.Table('u_data')
audit=dynamodb.Table('u_audit')

S3_config = Config(
    region_name = S3Region,
    signature_version = 's3v4',
    s3={'addressing_style': 'path'},
)
s3_client = boto3.client('s3', config=S3_config)


def lambda_handler(event, context):
    # Variables passed from API
    vs_id=event['v1'].replace(' ','')
    v_code=event['v2'].replace(' ','')
    f_name=event['v3'].strip()
    
    unacceptable_values = ['','<UserID>','UserID','<PassCode>','PassCode','<DocName>','DocName']

    if vs_id in unacceptable_values  or  v_code in unacceptable_values  or  f_name in unacceptable_values:
        return "Enter valid values for User ID against '<UserID>', Pass Code against '<PassCode>' and Document Name against '<DocName>' in the address bar URL."
    
    if vs_id.isdigit() == False:
        return "You entered - '" + vs_id + "', as a user id. Please enter a valid numeric user id which is shared with you over the email."
        
    if v_code.isdigit() == False:
        return "You entered - '" + v_code + "', as a pass code. Please enter a valid numeric pass code which is shared with you over the email."
        
    v_id = int(vs_id)
    response = userdata.get_item(Key={'u_id': v_id}, AttributesToGet=['u_code','u_name','u_status'])
    
    # If user is not registered then end the process by sending a message
    if len(response) == 1:
        return "User ID you entered - " + vs_id + ", is not registered. Please provide a valid User ID."
        
    # Check if file name provided is part of the shared document list. If not then exit the process asking user to provide a valid file name

    file_exists = False
    
    for bucket_objects in s3_client.list_objects_v2(Bucket=S3Bucket) ['Contents']:
        if f_name == bucket_objects['Key'].strip('[]'):
            file_exists = True
            break

    if not file_exists:
        return "The file name you provided - '" + f_name + "', is not part of the shared document list. Please provide a file name from the list shared with you over the email."
    
    # If user is registered then fetch the credential details from DB
    item = response['Item']
    u_code = item["u_code"]
    u_name = item["u_name"]
    u_status = item["u_status"]
    
    # Check if user is active
    if u_status != 'approved':
        return "You registration status is not approved. Please contact the administrator to get it approved to access the documents."
    
    # If user has passed the incorrect code i.e. he/she is an unauthorized user
    if u_code != str(v_code):
        return "Either you are using an incorrect pass-code or the one which you have already used once. Please use the correct value or re-generate a pass-code or contact system administrator."
    
    # If pass-code is correct then proceed with the creation of the PreSigned URL
    #presigned_url=s3_client.generate_presigned_url(ClientMethod='get_object',Params={'Bucket':S3Bucket,'Key':S3Folder+f_name},ExpiresIn=ExpiresInSec, HttpMethod=None)
    presigned_url=s3_client.generate_presigned_url(ClientMethod='get_object',Params={'Bucket':S3Bucket,'Key':f_name},ExpiresIn=ExpiresInSec, HttpMethod=None)
    
    # Make an entry to the Audit table about the above activity
    dateTimeObj = str(datetime.now())
    audit.put_item(Item={'u_id': v_id, 'u_name': u_name, 'file_name': f_name, 'u_access_time': dateTimeObj})
    
    # Clear the pass-code present in the system so that it won't be used twice
    ncode = str(random.randint(1000000,9999999)) # different range is used to avoid overlap with numbers generated in f-pass-code-generation function
    userdata.update_item(Key={'u_id': v_id}, UpdateExpression='set u_code = :u',ExpressionAttributeValues={':u': ncode})
    
    # Publish a mesage on the front-end with a PreSigned URL
    return "Welcome "+ u_name + "! You can access "+ f_name +" with below URL only for next " + ExpiresInSec + " secs starting from " + dateTimeObj + " UTC --> " + presigned_url