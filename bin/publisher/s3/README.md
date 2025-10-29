- Configure AWS profiles:
  - `C:\Users\<user>\.aws`

aws configure list-profiles
set AWS_PROFILE=cicd
aws sso login --profile cicd
aws s3 cp s3://downloads.robocorp.com/gallery/actions/ ./s3-actions/ --recursive