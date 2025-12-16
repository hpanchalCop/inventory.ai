# AWS ECS Deployment Guide

This directory contains automated deployment scripts and configuration files for deploying Inventory.AI to AWS ECS Fargate with RDS PostgreSQL.

## 🚀 Quick Start (Recommended)

The **modular deployment script** automates the entire infrastructure setup:

```powershell
cd deployment
.\deploy-modular.ps1
```

This single command creates:
- ✅ VPC Security Groups (ALB, ECS, RDS)
- ✅ RDS PostgreSQL with pgvector
- ✅ AWS Secrets Manager for credentials
- ✅ IAM Roles (Task Execution & Task Role)
- ✅ ECR Repositories
- ✅ Application Load Balancer with routing
- ✅ ECS Cluster and Services (API + Dashboard)
- ✅ CloudWatch Log Groups

## 📁 File Structure

```
deployment/
├── config.json                      # Central configuration file ⚙️
├── task-definition-api.json         # API container template
├── task-definition-dashboard.json   # Dashboard container template
├── deploy-modular.ps1              # Automated deployment script (NEW)
├── deploy-to-aws.ps1               # Legacy deployment script
├── deployment-info.json            # Generated deployment details
└── README.md                       # This file
```

## 🎯 Deployment Options

### Full Deployment (API + Dashboard)
```powershell
.\deploy-modular.ps1
```

### Deploy API Only
```powershell
.\deploy-modular.ps1 -ApiOnly
```

### Deploy Dashboard Only
```powershell
.\deploy-modular.ps1 -DashboardOnly
```

### Skip Docker Build (Use Existing Images)
```powershell
.\deploy-modular.ps1 -SkipImageBuild
```

### Push Only (Skip Build, Push Existing)
```powershell
.\deploy-modular.ps1 -PushOnly
```

### Use Custom Config File
```powershell
.\deploy-modular.ps1 -ConfigFile "./config-staging.json"
```

## 🌐 Access URLs

After deployment:

- **API Base**: `http://<alb-dns>/`
- **API Docs**: `http://<alb-dns>/docs` (Swagger UI)
- **API Health**: `http://<alb-dns>/health`
- **Dashboard**: `http://<alb-dns>/dashboard`

The ALB DNS name is displayed at the end of deployment and saved in `deployment-info.json`.

## ⚙️ Configuration

### Main Config: `config.json`

Edit this file to customize your deployment:

```json
{
  "projectName": "inventory-ai",
  "region": "us-east-1",
  "accountId": "030540333303",
  "vpcId": "vpc-02298a9bd94ceb77b",
  
  "database": {
    "instanceClass": "db.t3.micro",
    "masterPassword": "YourSecurePassword123!"
  },
  
  "ecs": {
    "api": {
      "taskCpu": "2048",
      "taskMemory": "4096",
      "desiredCount": 2
    },
    "dashboard": {
      "taskCpu": "1024",
      "taskMemory": "2048",
      "desiredCount": 1
    }
  }
}
```

### Task Definition Templates

Templates use `{{Placeholders}}` replaced during deployment:
- `{{ECSTaskCPU}}` - CPU units from config
- `{{ECSTaskMemory}}` - Memory in MB
- `{{ECRImageUri}}` - Auto-generated ECR image URI
- `{{SecretArn}}` - Secrets Manager ARN
- `{{ApiUrl}}` - Internal API URL for Dashboard

## 🔧 Common Configuration Changes

### Change ECS Resources
Edit `config.json`:
```json
"ecs": {
  "api": {
    "taskCpu": "4096",      // Increase CPU
    "taskMemory": "8192",   // Increase memory
    "desiredCount": 4       // Scale to 4 tasks
  }
}
```

Redeploy:
```powershell
.\deploy-modular.ps1 -ApiOnly -SkipImageBuild
```

### Update Database Password
1. Edit password in `config.json`
2. Update RDS:
   ```powershell
   aws rds modify-db-instance --db-instance-identifier inventory-ai-db --master-user-password "NewPassword123!" --apply-immediately
   ```
3. Redeploy to update secrets:
   ```powershell
   .\deploy-modular.ps1 -SkipImageBuild
   ```

### Add Environment Variable
Edit task definition JSON:
```json
"environment": [
  { "name": "NEW_VAR", "value": "new_value" }
]
```

Redeploy:
```powershell
.\deploy-modular.ps1 -ApiOnly -SkipImageBuild
```


## 🏗️ Architecture

### Services
- **API Service**: FastAPI on port 8000 (default ALB route)
- **Dashboard Service**: Dash/Plotly on port 8050 (`/dashboard*` path)

### Load Balancer Routing
```
ALB (Port 80)
├── Default Action → API Target Group (port 8000)
└── Rule: /dashboard* → Dashboard Target Group (port 8050)
```

### Security Groups
```
Internet (0.0.0.0/0) → ALB SG (Port 80)
                       ↓
ALB SG → ECS SG (Ports 8000, 8050)
         ↓
ECS SG → RDS SG (Port 5432)
```

### Network Flow
1. User requests `http://alb-dns/docs` → API service
2. User requests `http://alb-dns/dashboard` → Dashboard service
3. Both services connect to RDS PostgreSQL
4. Services use Secrets Manager for credentials

## 📊 Monitoring

### View Logs
```powershell
# API logs (live tail)
aws logs tail /ecs/inventory-ai-api --follow

# Dashboard logs
aws logs tail /ecs/inventory-ai-dashboard --follow

# Last 5 minutes of API logs
aws logs tail /ecs/inventory-ai-api --since 5m

# Filter logs for errors
aws logs tail /ecs/inventory-ai-api --follow --filter-pattern ERROR
```

### Check Service Status
```powershell
# Check all services
aws ecs describe-services --cluster inventory-ai-cluster --services inventory-ai-api-service inventory-ai-dashboard-service

# Check running tasks
aws ecs list-tasks --cluster inventory-ai-cluster --service-name inventory-ai-api-service

# View task details
aws ecs describe-tasks --cluster inventory-ai-cluster --tasks <task-arn>
```

### CloudWatch Metrics
```powershell
# View CPU utilization
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ServiceName,Value=inventory-ai-api-service Name=ClusterName,Value=inventory-ai-cluster --statistics Average --start-time 2025-12-15T00:00:00Z --end-time 2025-12-15T23:59:59Z --period 3600
```

## 🔍 Troubleshooting

### Tasks Not Starting

**Symptoms**: Service shows 0 running tasks, tasks keep stopping

**Solutions**:
1. Check CloudWatch logs for startup errors:
   ```powershell
   aws logs tail /ecs/inventory-ai-api --since 10m
   ```

2. Verify ECR images exist:
   ```powershell
   aws ecr describe-images --repository-name inventory-ai/api
   ```

3. Check task definition CPU/memory limits:
   ```powershell
   aws ecs describe-task-definition --task-definition inventory-ai-api
   ```

4. Verify IAM role permissions:
   ```powershell
   aws iam get-role --role-name inventory-ai-ecs-task-execution-role
   ```

### Database Connection Issues

**Symptoms**: Tasks start but fail health checks, logs show "password authentication failed"

**Solutions**:
1. Verify password matches between `config.json` and RDS:
   ```powershell
   # Check current password in Secrets Manager
   aws secretsmanager get-secret-value --secret-id inventory-ai/prod/env --query SecretString
   ```

2. Reset RDS password to match config:
   ```powershell
   aws rds modify-db-instance --db-instance-identifier inventory-ai-db --master-user-password "InventoryDB2143!Pass" --apply-immediately
   ```

3. Force tasks to restart and reload secrets:
   ```powershell
   aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-api-service --force-new-deployment
   ```

4. Check security group rules:
   ```powershell
   # RDS security group should allow port 5432 from ECS security group
   aws ec2 describe-security-groups --group-ids <rds-sg-id>
   ```

### Dashboard Not Accessible

**Symptoms**: API works but `/dashboard` returns 503

**Solutions**:
1. Verify dashboard task is running:
   ```powershell
   aws ecs describe-services --cluster inventory-ai-cluster --services inventory-ai-dashboard-service
   ```

2. Check listener rule exists for `/dashboard*`:
   ```powershell
   aws elbv2 describe-rules --listener-arn <listener-arn>
   ```

3. Verify target group health:
   ```powershell
   aws elbv2 describe-target-health --target-group-arn <dashboard-tg-arn>
   ```

4. Check dashboard logs:
   ```powershell
   aws logs tail /ecs/inventory-ai-dashboard --follow
   ```

### Health Checks Failing

**Symptoms**: Tasks start but ALB marks them unhealthy

**Solutions**:
1. Increase health check grace period in task definition
2. Verify health check paths are correct (`/health` for API, `/` for Dashboard)
3. Check if container is listening on correct port (8000 or 8050)
4. Test health check manually:
   ```powershell
   # Get task's public IP
   aws ecs describe-tasks --cluster inventory-ai-cluster --tasks <task-id> --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text
   
   # Curl the health endpoint
   curl http://<task-public-ip>:8000/health
   ```

### Image Pull Errors

**Symptoms**: Tasks fail immediately with "CannotPullContainerError"

**Solutions**:
1. Verify ECR authentication:
   ```powershell
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   ```

2. Check task execution role has ECR permissions:
   ```powershell
   aws iam get-role-policy --role-name inventory-ai-ecs-task-execution-role --policy-name AmazonECSTaskExecutionRolePolicy
   ```

3. Verify image exists in ECR:
   ```powershell
   aws ecr describe-images --repository-name inventory-ai/api --image-ids imageTag=latest
   ```

## 💰 Cost Optimization

### Development Environment
```powershell
# Use smaller instance sizes
# Edit config.json:
{
  "ecs": {
    "api": {
      "taskCpu": "512",
      "taskMemory": "1024",
      "desiredCount": 1
    }
  },
  "database": {
    "instanceClass": "db.t3.micro"
  }
}
```

### Spot Instances (Non-Production)
Manually update service to use FARGATE_SPOT:
```powershell
aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-api-service --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1
```

### Auto-Scaling
Create auto-scaling policies:
```powershell
# Register scalable target
aws application-autoscaling register-scalable-target --service-namespace ecs --resource-id service/inventory-ai-cluster/inventory-ai-api-service --scalable-dimension ecs:service:DesiredCount --min-capacity 1 --max-capacity 10

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy --service-namespace ecs --resource-id service/inventory-ai-cluster/inventory-ai-api-service --scalable-dimension ecs:service:DesiredCount --policy-name cpu-scaling --policy-type TargetTrackingScaling --target-tracking-scaling-policy-configuration '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"}}'
```

### Stop Non-Production Environments
```powershell
# Stop services (keeps infrastructure, stops tasks)
aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-api-service --desired-count 0
aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-dashboard-service --desired-count 0
```

## 🧹 Cleanup

To delete all deployed resources:

```powershell
# Stop and delete ECS services
aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-api-service --desired-count 0
aws ecs delete-service --cluster inventory-ai-cluster --service inventory-ai-api-service --force

aws ecs update-service --cluster inventory-ai-cluster --service inventory-ai-dashboard-service --desired-count 0
aws ecs delete-service --cluster inventory-ai-cluster --service inventory-ai-dashboard-service --force

# Delete ECS cluster
aws ecs delete-cluster --cluster inventory-ai-cluster

# Delete Load Balancer and Target Groups
aws elbv2 delete-load-balancer --load-balancer-arn <alb-arn>
aws elbv2 delete-target-group --target-group-arn <api-tg-arn>
aws elbv2 delete-target-group --target-group-arn <dashboard-tg-arn>

# Delete RDS instance (CAUTION: This deletes your database!)
aws rds delete-db-instance --db-instance-identifier inventory-ai-db --skip-final-snapshot

# Delete ECR repositories
aws ecr delete-repository --repository-name inventory-ai/api --force
aws ecr delete-repository --repository-name inventory-ai/dashboard --force

# Delete Secrets Manager secret
aws secretsmanager delete-secret --secret-id inventory-ai/prod/env --force-delete-without-recovery

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /ecs/inventory-ai-api
aws logs delete-log-group --log-group-name /ecs/inventory-ai-dashboard

# Delete Security Groups (after other resources are deleted)
aws ec2 delete-security-group --group-id <alb-sg-id>
aws ec2 delete-security-group --group-id <ecs-sg-id>
aws ec2 delete-security-group --group-id <rds-sg-id>
```

**Note**: Get resource ARNs/IDs from `deployment-info.json`

## 📚 Migration from Legacy Script

If you're currently using `deploy-to-aws.ps1`:

### Migration Steps:

1. **Backup current deployment info**:
   ```powershell
   cp deployment-info.json deployment-info-backup.json
   ```

2. **Extract settings to config.json**:
   - Copy RDS password from `deployment-info.json`
   - Verify all settings in `config.json` match your infrastructure

3. **Test with existing resources**:
   ```powershell
   .\deploy-modular.ps1 -SkipImageBuild
   ```
   This will update task definitions without rebuilding images

4. **Switch to new script**:
   Use `deploy-modular.ps1` for all future deployments

### Key Differences:

| Feature | Legacy Script | Modular Script |
|---------|--------------|----------------|
| Configuration | Hardcoded in script | External `config.json` |
| Dashboard Support | ❌ No | ✅ Yes |
| Partial Deploys | ❌ No | ✅ Yes (-ApiOnly, -DashboardOnly) |
| Task Definitions | Inline PowerShell | JSON templates |
| Password Generation | Random each run | Fixed from config |

## 🎓 Best Practices

1. **Version Control**
   - ✅ Commit `config.json`, `task-definition-*.json`
   - ❌ Do NOT commit `deployment-info.json` (contains generated IDs)
   - ❌ Do NOT commit passwords in config (use environment-specific files)

2. **Multiple Environments**
   - Create separate configs: `config-dev.json`, `config-staging.json`, `config-prod.json`
   - Use different VPCs/accounts per environment
   - Deploy with: `.\deploy-modular.ps1 -ConfigFile config-prod.json`

3. **Secrets Management**
   - Consider moving sensitive values to AWS Systems Manager Parameter Store
   - Use IAM roles instead of access keys where possible
   - Rotate credentials regularly

4. **Incremental Updates**
   - For code changes only: Use `-PushOnly -ApiOnly` (fastest)
   - For config changes: Use `-SkipImageBuild` (skips Docker build)
   - For full rebuild: Run without flags

5. **Monitoring Setup**
   - Enable Container Insights for detailed metrics
   - Set up CloudWatch alarms for high CPU/memory
   - Configure SNS notifications for task failures

6. **Testing Strategy**
   - Always test changes in dev environment first
   - Use blue-green deployment for production updates
   - Keep previous task definition versions for rollback

## 🔗 Related Documentation

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [Fargate Task Definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [ALB Routing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html)
- [RDS PostgreSQL with pgvector](https://github.com/pgvector/pgvector)

## 🆘 Support

**Issues or Questions?**

1. Check CloudWatch Logs for error details
2. Review `deployment-info.json` for resource ARNs
3. Verify configuration in `config.json`
4. Check AWS service quotas and limits
5. Consult troubleshooting section above

**Deployment Info Location**: `deployment/deployment-info.json` contains all deployed resource identifiers and endpoints.

