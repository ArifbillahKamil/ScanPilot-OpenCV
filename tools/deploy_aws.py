"""Review the deployment locally; --apply explicitly creates billable AWS resources."""
import argparse
import base64
import datetime
from pathlib import Path
import subprocess

import boto3
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region',required=True)
    parser.add_argument('--profile')
    parser.add_argument('--stack',default='scanpilot-demo')
    parser.add_argument('--repository',default='scanpilot')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(f'Plan: region={args.region}, stack={args.stack}, ECR={args.repository}')
    print('Build linux/amd64 image; push to ECR; deploy ECS Express (2 vCPU / 4 GB, 1-2 tasks).')
    print('Express Mode provisions a load balancer, TLS, networking, scaling and CloudWatch resources.')
    print('CloudFormation also creates two IAM roles and a Secrets Manager demo password.')
    print('Images are processed in memory. No document bucket or document history is created.')
    if not args.apply:
        print('Plan only. No AWS calls made. Add --apply only when ready to create billable resources.')
        return
    # Fail before creating resources if Docker is unavailable.
    subprocess.run(['docker','version'],check=True,stdout=subprocess.DEVNULL)
    session=boto3.Session(profile_name=args.profile,region_name=args.region)
    session.client('sts').get_caller_identity()
    if not session.client('ec2').describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']:
        raise SystemExit('No default VPC in this region. Configure NetworkConfiguration in infra/ecs-express.yaml before deployment.')
    ecr=session.client('ecr')
    try:
        repo=ecr.describe_repositories(repositoryNames=[args.repository])['repositories'][0]
    except ecr.exceptions.RepositoryNotFoundException:
        repo=ecr.create_repository(repositoryName=args.repository,imageTagMutability='IMMUTABLE',
                                   imageScanningConfiguration={'scanOnPush':True})['repository']
    tag=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    uri=f"{repo['repositoryUri']}:{tag}"
    subprocess.run(['docker','build','--platform','linux/amd64','-t',uri,'.'],cwd=ROOT,check=True)
    auth=ecr.get_authorization_token()['authorizationData'][0]
    username,password=base64.b64decode(auth['authorizationToken']).decode().split(':',1)
    subprocess.run(['docker','login','--username',username,'--password-stdin',auth['proxyEndpoint']],
                   input=password.encode(),check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['docker','push',uri],check=True)
    cf=session.client('cloudformation')
    template=(ROOT/'infra/ecs-express.yaml').read_text(encoding='utf-8')
    cf.validate_template(TemplateBody=template)
    parameters=[{'ParameterKey':'ImageUri','ParameterValue':uri}]
    values=dict(StackName=args.stack,TemplateBody=template,Parameters=parameters,Capabilities=['CAPABILITY_IAM'])
    try:
        cf.describe_stacks(StackName=args.stack)
    except ClientError as error:
        if 'does not exist' not in str(error): raise
        cf.create_stack(**values)
        waiter='stack_create_complete'
    else:
        cf.update_stack(**values)
        waiter='stack_update_complete'
    print('Waiting for CloudFormation. View stack events in the AWS console if deployment fails.')
    cf.get_waiter(waiter).wait(StackName=args.stack,WaiterConfig={'Delay':20,'MaxAttempts':90})
    outputs=cf.describe_stacks(StackName=args.stack)['Stacks'][0].get('Outputs',[])
    for item in outputs:
        print(item['OutputKey']+': '+item['OutputValue'])
    print('Username: scanpilot. Retrieve the password privately from the Secrets Manager console.')
    print('Smoke test /api/health and the two-photo example on the deployed URL before claiming AWS validation.')


if __name__=='__main__':
    main()
