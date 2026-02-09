# AWS Phase 1 - Post-Deployment Configuration

## Current Status ✅

### Completed:
- [x] All AWS resources created (RDS, ElastiCache, S3, Lambda, API Gateway, Amplify)
- [x] GitHub secrets configured
- [x] Local environment variables updated
- [x] Code pushed to trigger CI/CD deployment
- [x] Amplify frontend deployed (showing welcome page - needs rebuild)

### Remaining Configuration:

---

## 1. Configure API Gateway Routes

Your API Gateway is currently showing "Not Found" because it needs catch-all route configuration.

### Steps:

1. Go to **API Gateway Console**: https://ca-west-1.console.aws.amazon.com/apigateway
2. Click on `compliance-platform-api-gateway`
3. Click **"Routes"** in the left sidebar
4. You should see routes configured. If not, add:
   - Click **"Create"**
   - **Route**: `ANY /{proxy+}`
   - **Integration**: Select your Lambda function `compliance-platform-api`
   - Click **"Create"**
5. Add root route:
   - Click **"Create"** again
   - **Route**: `ANY /`
   - **Integration**: Select your Lambda function `compliance-platform-api`
   - Click **"Create"**
6. Click **"Deploy"** → Select or create a stage (e.g., `$default`)

### Test After Configuration:
```powershell
curl https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/health
```

Expected response: `{"status": "healthy", ...}`

---

## 2. Trigger Amplify Frontend Build

The Amplify app needs to rebuild with your actual code.

### Steps:

1. Go to **Amplify Console**: https://console.aws.amazon.com/amplify
2. Click on your app (should be linked to `KulbirJ/Risk-Management`)
3. You should see a build in progress OR
4. If no build started:
   - Click **"Run build"** or **"Redeploy this version"**
5. Wait for build to complete (3-5 minutes)
6. Check build logs if it fails

### Verify Environment Variables:
- Go to **App settings** → **Environment variables**
- Ensure these are set:
  ```
  NEXT_PUBLIC_API_URL = https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com
  NEXT_PUBLIC_AWS_REGION = ca-west-1
  ```

### Test After Build:
```powershell
curl https://main.dxvwwyu86swrl.amplifyapp.com/
```

Expected: Your compliance platform UI (not AWS welcome page)

---

## 3. Run Database Migrations

Migrations will run automatically after Lambda deployment completes. You can also trigger them manually:

### Option A: Wait for GitHub Actions Deployment
1. Check GitHub Actions: https://github.com/KulbirJ/Risk-Management/actions
2. Wait for "Deploy to AWS Lambda & Amplify" workflow to complete
3. Migrations run as part of the workflow

### Option B: Manual Trigger via AWS CLI
```powershell
aws lambda invoke `
  --function-name compliance-platform-api `
  --payload '{"action":"run_migrations"}' `
  --region ca-west-1 `
  migration-response.json

Get-Content migration-response.json
```

### Option C: Temporarily Enable RDS Public Access
**Only if you need to run migrations from your local machine:**

1. Go to **RDS Console**: https://ca-west-1.console.aws.amazon.com/rds
2. Select `compliance-platform-db-dev`
3. Click **"Modify"**
4. Scroll to **"Connectivity"** → **"Public access"** → Select **"Yes"**
5. Click **"Continue"** → **"Apply immediately"**
6. Wait for modification to complete (5-10 minutes)
7. Add your IP to security group:
   - Go to **EC2** → **Security Groups**
   - Find `compliance-platform-rds-sg-dev`
   - Edit inbound rules
   - Add rule: PostgreSQL (5432) from YOUR_IP/32
8. Run migrations:
   ```powershell
   cd "c:\Users\user1-baseNaultha\Threat Risk Assessment\compliance-platform-mvp"
   docker-compose exec backend bash -c "cd /app/backend && DATABASE_URL='postgresql://complianceadmin:g#K*^58]&bRN:qe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres' python -m alembic -c app/db/alembic/alembic.ini upgrade head"
   ```
9. **IMPORTANT:** After migrations, disable public access:
   - Go back to RDS → Modify
   - Set **"Public access"** to **"No"**
   - Remove your IP from security group

---

## 4. Check GitHub Actions Workflow Status

1. Visit: https://github.com/KulbirJ/Risk-Management/actions
2. Look for the latest "Deploy to AWS Lambda & Amplify" workflow
3. Check if it's:
   - ✅ **Running**: Wait for completion
   - ✅ **Succeeded**: Lambda is deployed
   - ❌ **Failed**: Click to view logs and troubleshoot

### Common Issues:
- **Missing secrets**: Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
- **Permission errors**: Check IAM user has Lambda and deployment permissions
- **Build errors**: Check Python dependencies in requirements

---

## 5. Update Lambda Environment Variables

Ensure Lambda has the correct environment variables:

1. Go to **Lambda Console**: https://ca-west-1.console.aws.amazon.com/lambda
2. Click on `compliance-platform-api`
3. Go to **Configuration** → **Environment variables**
4. Click **"Edit"**
5. Verify/Update:
   ```
   DATABASE_URL = postgresql://complianceadmin:g#K*^58]&bRN:qe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres
   REDIS_URL = redis://compliance-platform-cache-dev.scwc1g.0001.caw1.cache.amazonaws.com:6379/0
   AWS_REGION_NAME = ca-west-1
   S3_BUCKET_NAME = compliance-platform-evidence-dev
   ENVIRONMENT = dev
   ```
6. Click **"Save"**

---

## 6. Test the Complete Application

### Test API Gateway + Lambda:
```powershell
# Health check
curl https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/health

# API docs
curl https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/docs
```

### Test Frontend:
Open browser: https://main.dxvwwyu86swrl.amplifyapp.com/

### Test Database Connection:
```powershell
# Option 1: Via Lambda (if public access is disabled)
aws lambda invoke `
  --function-name compliance-platform-api `
  --payload '{"action":"health_check"}' `
  --region ca-west-1 `
  health-response.json

Get-Content health-response.json

# Option 2: Direct connection (if public access is enabled)
psql -h compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com -U complianceadmin -d postgres
# Password: g#K*^58]&bRN:qe
```

---

## 7. Monitor and Troubleshoot

### CloudWatch Logs:
1. **Lambda Console** → `compliance-platform-api` → **Monitor** → **View CloudWatch logs**
2. Check for errors in Lambda execution

### Amplify Build Logs:
1. **Amplify Console** → Your app → Click on build → **Build logs**
2. Check for frontend build errors

### RDS Monitoring:
1. **RDS Console** → `compliance-platform-db-dev` → **Monitoring**
2. Check connections, CPU, storage

---

## Summary of Endpoints

| Resource | URL/Endpoint |
|----------|--------------|
| **API Gateway** | https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com |
| **Amplify Frontend** | https://main.dxvwwyu86swrl.amplifyapp.com |
| **RDS Endpoint** | compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432 |
| **ElastiCache** | compliance-platform-cache-dev.scwc1g.0001.caw1.cache.amazonaws.com:6379 |
| **GitHub Actions** | https://github.com/KulbirJ/Risk-Management/actions |

---

## Next Steps After Testing

1. ✅ Verify all endpoints return expected responses
2. ✅ Test user authentication flow (Phase 2 with Cognito)
3. ✅ Test file uploads to S3
4. ✅ Monitor CloudWatch for errors
5. ✅ Set up CloudWatch alarms for monitoring
6. ✅ Review and optimize Lambda performance
7. ✅ Plan Phase 2: Add Cognito authentication

---

## Quick Reference Commands

```powershell
# Check GitHub Actions status
Start-Process "https://github.com/KulbirJ/Risk-Management/actions"

# Test API
curl https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/health

# Test Frontend
Start-Process "https://main.dxvwwyu86swrl.amplifyapp.com"

# Run migrations via Lambda
aws lambda invoke --function-name compliance-platform-api --payload '{\"action\":\"run_migrations\"}' --region ca-west-1 migration-response.json; Get-Content migration-response.json

# Check Lambda logs
aws logs tail /aws/lambda/compliance-platform-api --follow --region ca-west-1
```

---

## Estimated Timeline

- **API Gateway Route Configuration**: 5 minutes
- **Amplify Build Trigger**: 3-5 minutes
- **GitHub Actions Deployment**: 5-10 minutes
- **Database Migrations**: 1-2 minutes
- **Testing**: 10-15 minutes

**Total**: ~30-45 minutes

---

## Need Help?

Check these resources:
- **AWS Lambda Logs**: CloudWatch → Log groups → `/aws/lambda/compliance-platform-api`
- **API Gateway Logs**: CloudWatch → Log groups → API-Gateway-Execution-Logs
- **Amplify Build Logs**: Amplify Console → App → Build history
- **GitHub Actions**: Repository → Actions tab
