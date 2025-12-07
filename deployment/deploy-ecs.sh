#!/bin/bash
# Deploy to AWS ECS

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY}
CLUSTER_NAME=${CLUSTER_NAME:-inventory-ai-cluster}
API_SERVICE_NAME=${API_SERVICE_NAME:-inventory-ai-api-service}
DASHBOARD_SERVICE_NAME=${DASHBOARD_SERVICE_NAME:-inventory-ai-dashboard-service}

# Check required environment variables
if [ -z "$ECR_REGISTRY" ]; then
    echo "Error: ECR_REGISTRY environment variable is not set"
    exit 1
fi

echo "Building and pushing Docker images..."

# Build and push API image
echo "Building API image..."
docker build -f Dockerfile.api -t ${ECR_REGISTRY}/inventory-ai-api:latest .
echo "Pushing API image to ECR..."
docker push ${ECR_REGISTRY}/inventory-ai-api:latest

# Build and push Dashboard image
echo "Building Dashboard image..."
docker build -f Dockerfile.dashboard -t ${ECR_REGISTRY}/inventory-ai-dashboard:latest .
echo "Pushing Dashboard image to ECR..."
docker push ${ECR_REGISTRY}/inventory-ai-dashboard:latest

echo "Registering task definitions..."

# Register API task definition
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs-task-definition-api.json \
    --region ${AWS_REGION}

# Register Dashboard task definition
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs-task-definition-dashboard.json \
    --region ${AWS_REGION}

echo "Updating services..."

# Update API service
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${API_SERVICE_NAME} \
    --task-definition inventory-ai-api \
    --force-new-deployment \
    --region ${AWS_REGION}

# Update Dashboard service
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${DASHBOARD_SERVICE_NAME} \
    --task-definition inventory-ai-dashboard \
    --force-new-deployment \
    --region ${AWS_REGION}

echo "Deployment initiated successfully!"
echo "Monitor deployment status in AWS ECS Console"
