# S3 Actions Manifest Regeneration (Admin Only)

If for whatever reason we run into a case where the action pack manifests are broken or missing versions, with this folder and guide we are able to regenerate the manifest based on the S3 content. The Action Packs and old versions are all there, we need to "just":
- Load the S3 content locally
- Regenerate the manifest files
- Push the updates back to S3

**Requires:** 
- Git Bash on Windows
- AWS cli setup on the machine
- AWS CICD account with `ProductionAccountAdmin` role.

`~/.aws/config` should have:
```
[profile cicd-admin]
region = eu-west-1
sso_start_url = https://d-9067b8f409.awsapps.com/start/#
sso_region = us-east-1
sso_account_id = 710450854638
sso_role_name = ProductionAccountAdmin
output = json
```

Login the aws cli:
```
export AWS_PROFILE=cicd-admin
aws sso login --profile cicd-admin
```

## Steps

Run the commands in the `/publisher` -root folder

1. Download S3 content:
   ```
   aws s3 cp s3://downloads.robocorp.com/gallery/actions/ ./s3/s3-actions/ --recursive
   ```

2. Regenerate manifests:
   ```
   rcc run -t "Regen actions manifests"
   ```
   Use `SKIP_CLEAN=1` to skip cache clearing for faster runs if whitelist unchanged.

3. Upload to S3:
   ```
   ./s3/upload_regen_action_manifests.sh
   ```

4. Verify the manifests in AWS S3 or that action packs show up in Studio
