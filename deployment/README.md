# AWS ECS Deployment Configuration

This directory contains the configuration files for deploying inventory.ai to AWS ECS.

## Files

- `ecs-task-definition-api.json` - ECS task definition for the FastAPI service
- `ecs-task-definition-dashboard.json` - ECS task definition for the Dash dashboard
- `deploy-ecs.sh` - Deployment script

## Setup Instructions

### 1. Configure Placeholders

Before deploying, you need to replace the following placeholders in the task definition files:

#### In `ecs-task-definition-api.json` and `ecs-task-definition-dashboard.json`:

- `YOUR_ACCOUNT_ID` - Replace with your AWS account ID (e.g., `123456789012`)
- `YOUR_ECR_REGISTRY` - Replace with your ECR registry URL (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com`)
- `your-rds-endpoint` - Replace with your RDS PostgreSQL endpoint (e.g., `inventory-db.xxxxx.us-east-1.rds.amazonaws.com`)

You can use `sed` to replace these values:

```bash
# Replace YOUR_ACCOUNT_ID
sed -i 's/YOUR_ACCOUNT_ID/123456789012/g' ecs-task-definition-*.json

# Replace YOUR_ECR_REGISTRY
sed -i 's|YOUR_ECR_REGISTRY|123456789012.dkr.ecr.us-east-1.amazonaws.com|g' ecs-task-definition-*.json

# Replace your-rds-endpoint
sed -i 's/your-rds-endpoint/inventory-db.xxxxx.us-east-1.rds.amazonaws.com/g' ecs-task-definition-*.json
```

### 2. Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** installed and configured
2. **Docker** installed for building images
3. **ECR Repositories** created:
   ```bash
   aws ecr create-repository --repository-name inventory-ai-api
   aws ecr create-repository --repository-name inventory-ai-dashboard
   ```

4. **ECS Cluster** created:
   ```bash
   aws ecs create-cluster --cluster-name inventory-ai-cluster
   ```

5. **RDS PostgreSQL** instance with pgvector extension installed

6. **S3 Bucket** created:
   ```bash
   aws s3 mb s3://inventory-ai-bucket
   ```

7. **IAM Roles** created:
   - `ecsTaskExecutionRole` - For ECS to pull images and access secrets
   - `ecsTaskRole` - For containers to access AWS services (S3, Secrets Manager)

8. **Secrets Manager** secrets created:
   ```bash
   aws secretsmanager create-secret \
     --name inventory-ai/aws-credentials \
     --secret-string '{"AWS_ACCESS_KEY_ID":"xxx","AWS_SECRET_ACCESS_KEY":"yyy"}'
   ```

9. **CloudWatch Log Groups** created:
   ```bash
   aws logs create-log-group --log-group-name /ecs/inventory-ai-api
   aws logs create-log-group --log-group-name /ecs/inventory-ai-dashboard
   ```

### 3. Deploy

Set environment variables:

```bash
export ECR_REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
export CLUSTER_NAME=inventory-ai-cluster
export API_SERVICE_NAME=inventory-ai-api-service
export DASHBOARD_SERVICE_NAME=inventory-ai-dashboard-service
```

Run the deployment script:

```bash
./deploy-ecs.sh
```

## Manual Deployment Steps

If you prefer to deploy manually:

### 1. Authenticate to ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REGISTRY
```

### 2. Build and Push Images

```bash
# Build API image
docker build -f Dockerfile.api -t $ECR_REGISTRY/inventory-ai-api:latest .
docker push $ECR_REGISTRY/inventory-ai-api:latest

# Build Dashboard image
docker build -f Dockerfile.dashboard -t $ECR_REGISTRY/inventory-ai-dashboard:latest .
docker push $ECR_REGISTRY/inventory-ai-dashboard:latest
```

### 3. Register Task Definitions

```bash
aws ecs register-task-definition \
  --cli-input-json file://deployment/ecs-task-definition-api.json

aws ecs register-task-definition \
  --cli-input-json file://deployment/ecs-task-definition-dashboard.json
```

### 4. Create Services

```bash
# Create API service
aws ecs create-service \
  --cluster inventory-ai-cluster \
  --service-name inventory-ai-api-service \
  --task-definition inventory-ai-api \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"

# Create Dashboard service
aws ecs create-service \
  --cluster inventory-ai-cluster \
  --service-name inventory-ai-dashboard-service \
  --task-definition inventory-ai-dashboard \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Monitoring

View service status:

```bash
aws ecs describe-services \
  --cluster inventory-ai-cluster \
  --services inventory-ai-api-service inventory-ai-dashboard-service
```

View logs:

```bash
# API logs
aws logs tail /ecs/inventory-ai-api --follow

# Dashboard logs
aws logs tail /ecs/inventory-ai-dashboard --follow
```

## Troubleshooting

### Task fails to start

1. Check CloudWatch logs for error messages
2. Verify all environment variables are set correctly
3. Ensure RDS security group allows connections from ECS tasks
4. Verify IAM roles have necessary permissions

### Image pull errors

1. Verify ECR authentication
2. Check that images were pushed successfully
3. Ensure `ecsTaskExecutionRole` has ECR pull permissions

### Database connection issues

1. Verify RDS endpoint is correct
2. Check RDS security group rules
3. Ensure pgvector extension is installed on RDS
4. Verify database credentials

## Cost Optimization

- Use **FARGATE_SPOT** for non-production environments
- Set up **auto-scaling** based on CPU/memory utilization
- Use **Application Load Balancer** health checks
- Enable **container insights** for detailed metrics
