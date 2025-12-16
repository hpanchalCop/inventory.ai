# Inventory.AI AWS Deployment Script
# Automated deployment to ECS Fargate with RDS PostgreSQL

param(
    [string]$Region = "us-east-1",
    [string]$AccountId = "030540333303",
    [string]$VpcId = "vpc-02298a9bd94ceb77b",
    [switch]$SkipImageBuild,
    [switch]$PushOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Inventory.AI AWS Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$config = @{
    ProjectName = "inventory-ai"
    Region = $Region
    AccountId = $AccountId
    VpcId = $VpcId
    RDSMasterPassword = "InventoryDB$(Get-Random -Minimum 1000 -Maximum 9999)!Pass"
    
    # Database
    RDSInstanceClass = "db.t3.micro"  # Small for POC (change to db.t3.medium for production)
    RDSAllocatedStorage = 20
    RDSEngine = "postgres"
    RDSEngineVersion = "15.8"
    
    # ECS
    ECSTaskCPU = "2048"
    ECSTaskMemory = "4096"
    ECSDesiredCount = 2
    
    # From environment variables
    Auth0Domain = $env:AUTH0_DOMAIN
    Auth0ClientId = $env:AUTH0_CLIENT_ID
    Auth0ClientSecret = $env:AUTH0_CLIENT_SECRET
    Auth0ApiAudience = $env:AUTH0_API_AUDIENCE
    AWSAccessKeyId = $env:AWS_ACCESS_KEY_ID
    AWSSecretAccessKey = $env:AWS_SECRET_ACCESS_KEY
    S3BucketName = $env:S3_BUCKET_NAME
}

# Get 2 subnets in different AZs from default VPC
Write-Host "[1/12] Getting VPC subnets..." -ForegroundColor Yellow
$subnets = aws ec2 describe-subnets `
    --filters "Name=vpc-id,Values=$($config.VpcId)" `
    --query 'Subnets[?MapPublicIpOnLaunch==`true`].[SubnetId,AvailabilityZone]' `
    --output json | ConvertFrom-Json

$subnet1 = $subnets[0][0]
$subnet2 = $subnets[1][0]
$az1 = $subnets[0][1]
$az2 = $subnets[1][1]

Write-Host "  ✓ Using subnets: $subnet1 ($az1), $subnet2 ($az2)" -ForegroundColor Green

# Step 1: Create Security Groups
Write-Host "`n[2/12] Creating Security Groups..." -ForegroundColor Yellow

# ALB Security Group
$albSgId = aws ec2 create-security-group `
    --group-name "$($config.ProjectName)-alb-sg" `
    --description "Security group for ALB" `
    --vpc-id $config.VpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $albSgId) {
    $albSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.ProjectName)-alb-sg" "Name=vpc-id,Values=$($config.VpcId)" `
        --query 'SecurityGroups[0].GroupId' `
        --output text
    Write-Host "  ✓ ALB Security Group already exists: $albSgId" -ForegroundColor Green
} else {
    aws ec2 authorize-security-group-ingress `
        --group-id $albSgId `
        --protocol tcp `
        --port 80 `
        --cidr 0.0.0.0/0 | Out-Null
    Write-Host "  ✓ Created ALB Security Group: $albSgId" -ForegroundColor Green
}

# ECS Task Security Group
$ecsSgId = aws ec2 create-security-group `
    --group-name "$($config.ProjectName)-ecs-sg" `
    --description "Security group for ECS tasks" `
    --vpc-id $config.VpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $ecsSgId) {
    $ecsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.ProjectName)-ecs-sg" "Name=vpc-id,Values=$($config.VpcId)" `
        --query 'SecurityGroups[0].GroupId' `
        --output text
    Write-Host "  ✓ ECS Security Group already exists: $ecsSgId" -ForegroundColor Green
} else {
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol tcp `
        --port 8000 `
        --source-group $albSgId | Out-Null
    
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol -1 `
        --source-group $ecsSgId | Out-Null
    Write-Host "  ✓ Created ECS Security Group: $ecsSgId" -ForegroundColor Green
}

# RDS Security Group
$rdsSgId = aws ec2 create-security-group `
    --group-name "$($config.ProjectName)-rds-sg" `
    --description "Security group for RDS" `
    --vpc-id $config.VpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $rdsSgId) {
    $rdsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.ProjectName)-rds-sg" "Name=vpc-id,Values=$($config.VpcId)" `
        --query 'SecurityGroups[0].GroupId' `
        --output text
    Write-Host "  ✓ RDS Security Group already exists: $rdsSgId" -ForegroundColor Green
} else {
    aws ec2 authorize-security-group-ingress `
        --group-id $rdsSgId `
        --protocol tcp `
        --port 5432 `
        --source-group $ecsSgId | Out-Null
    Write-Host "  ✓ Created RDS Security Group: $rdsSgId" -ForegroundColor Green
}

# Step 2: Create RDS PostgreSQL Instance
Write-Host "`n[3/12] Creating RDS PostgreSQL instance..." -ForegroundColor Yellow

$rdsExists = aws rds describe-db-instances `
    --db-instance-identifier "$($config.ProjectName)-db" `
    --query 'DBInstances[0].DBInstanceStatus' `
    --output text 2>$null

if ($rdsExists) {
    Write-Host "  ✓ RDS instance already exists (Status: $rdsExists)" -ForegroundColor Green
    $rdsEndpoint = aws rds describe-db-instances `
        --db-instance-identifier "$($config.ProjectName)-db" `
        --query 'DBInstances[0].Endpoint.Address' `
        --output text
} else {
    # Create DB subnet group
    aws rds create-db-subnet-group `
        --db-subnet-group-name "$($config.ProjectName)-db-subnet-group" `
        --db-subnet-group-description "Subnet group for inventory.ai" `
        --subnet-ids $subnet1 $subnet2 2>$null | Out-Null
    
    Write-Host "  → Creating RDS instance (this takes 5-10 minutes)..." -ForegroundColor Cyan
    aws rds create-db-instance `
        --db-instance-identifier "$($config.ProjectName)-db" `
        --db-instance-class $config.RDSInstanceClass `
        --engine $config.RDSEngine `
        --engine-version $config.RDSEngineVersion `
        --master-username postgres `
        --master-user-password $config.RDSMasterPassword `
        --allocated-storage $config.RDSAllocatedStorage `
        --db-subnet-group-name "$($config.ProjectName)-db-subnet-group" `
        --vpc-security-group-ids $rdsSgId `
        --db-name inventory_db `
        --backup-retention-period 0 `
        --storage-encrypted `
        --no-publicly-accessible | Out-Null
    
    Write-Host "  → Waiting for RDS to become available..." -ForegroundColor Cyan
    aws rds wait db-instance-available --db-instance-identifier "$($config.ProjectName)-db"
    
    $rdsEndpoint = aws rds describe-db-instances `
        --db-instance-identifier "$($config.ProjectName)-db" `
        --query 'DBInstances[0].Endpoint.Address' `
        --output text
    
    Write-Host "  ✓ RDS instance created: $rdsEndpoint" -ForegroundColor Green
}

$databaseUrl = "postgresql://postgres:$($config.RDSMasterPassword)@${rdsEndpoint}:5432/inventory_db"

# Step 3: Create Secrets Manager Secret
Write-Host "`n[4/12] Creating Secrets Manager secret..." -ForegroundColor Yellow

$secretString = @{
    DATABASE_URL = $databaseUrl
    AUTH0_DOMAIN = $config.Auth0Domain
    AUTH0_CLIENT_ID = $config.Auth0ClientId
    AUTH0_CLIENT_SECRET = $config.Auth0ClientSecret
    AUTH0_API_AUDIENCE = $config.Auth0ApiAudience
    AWS_ACCESS_KEY_ID = $config.AWSAccessKeyId
    AWS_SECRET_ACCESS_KEY = $config.AWSSecretAccessKey
    S3_BUCKET_NAME = $config.S3BucketName
} | ConvertTo-Json -Compress

$secretArn = aws secretsmanager create-secret `
    --name "$($config.ProjectName)/prod/env" `
    --description "Production environment variables for inventory.ai" `
    --secret-string $secretString `
    --query 'ARN' `
    --output text 2>$null

if (-not $secretArn) {
    $secretArn = aws secretsmanager describe-secret `
        --secret-id "$($config.ProjectName)/prod/env" `
        --query 'ARN' `
        --output text
    
    aws secretsmanager update-secret `
        --secret-id "$($config.ProjectName)/prod/env" `
        --secret-string $secretString | Out-Null
    
    Write-Host "  ✓ Secret updated: $secretArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ Secret created: $secretArn" -ForegroundColor Green
}

# Step 4: Create IAM Roles
Write-Host "`n[5/12] Creating IAM roles..." -ForegroundColor Yellow

# Task Execution Role
$taskExecRoleName = "$($config.ProjectName)-ecs-task-execution-role"
$taskExecRoleArn = aws iam get-role --role-name $taskExecRoleName --query 'Role.Arn' --output text 2>$null

if (-not $taskExecRoleArn) {
    $trustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{
                    Service = "ecs-tasks.amazonaws.com"
                }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json -Depth 10
    
    aws iam create-role `
        --role-name $taskExecRoleName `
        --assume-role-policy-document $trustPolicy | Out-Null
    
    aws iam attach-role-policy `
        --role-name $taskExecRoleName `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" | Out-Null
    
    $secretsPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("secretsmanager:GetSecretValue")
                Resource = $secretArn
            }
        )
    } | ConvertTo-Json -Depth 10
    
    aws iam put-role-policy `
        --role-name $taskExecRoleName `
        --policy-name SecretsManagerReadPolicy `
        --policy-document $secretsPolicy | Out-Null
    
    $taskExecRoleArn = aws iam get-role --role-name $taskExecRoleName --query 'Role.Arn' --output text
    Write-Host "  ✓ Created Task Execution Role: $taskExecRoleArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ Task Execution Role exists: $taskExecRoleArn" -ForegroundColor Green
}

# Task Role
$taskRoleName = "$($config.ProjectName)-ecs-task-role"
$taskRoleArn = aws iam get-role --role-name $taskRoleName --query 'Role.Arn' --output text 2>$null

if (-not $taskRoleArn) {
    $trustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{
                    Service = "ecs-tasks.amazonaws.com"
                }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json -Depth 10
    
    aws iam create-role `
        --role-name $taskRoleName `
        --assume-role-policy-document $trustPolicy | Out-Null
    
    $taskPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket")
                Resource = @("arn:aws:s3:::$($config.S3BucketName)", "arn:aws:s3:::$($config.S3BucketName)/*")
            },
            @{
                Effect = "Allow"
                Action = @("logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams")
                Resource = "arn:aws:logs:*:*:*"
            },
            @{
                Effect = "Allow"
                Action = @("cloudwatch:PutMetricData", "cloudwatch:GetMetricStatistics", "cloudwatch:ListMetrics")
                Resource = "*"
            }
        )
    } | ConvertTo-Json -Depth 10
    
    aws iam put-role-policy `
        --role-name $taskRoleName `
        --policy-name InventoryAITaskPolicy `
        --policy-document $taskPolicy | Out-Null
    
    $taskRoleArn = aws iam get-role --role-name $taskRoleName --query 'Role.Arn' --output text
    Write-Host "  ✓ Created Task Role: $taskRoleArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ Task Role exists: $taskRoleArn" -ForegroundColor Green
}

# Step 5: Create CloudWatch Log Group
Write-Host "`n[6/12] Creating CloudWatch log group..." -ForegroundColor Yellow

aws logs create-log-group --log-group-name "/ecs/$($config.ProjectName)-api" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Log group created: /ecs/$($config.ProjectName)-api" -ForegroundColor Green
} else {
    Write-Host "  ✓ Log group already exists: /ecs/$($config.ProjectName)-api" -ForegroundColor Green
}

aws logs put-retention-policy `
    --log-group-name "/ecs/$($config.ProjectName)-api" `
    --retention-in-days 7 | Out-Null

# Step 6: Create ECR Repository
Write-Host "`n[7/12] Creating ECR repository..." -ForegroundColor Yellow

$ecrUri = aws ecr describe-repositories `
    --repository-names "$($config.ProjectName)/api" `
    --query 'repositories[0].repositoryUri' `
    --output text 2>$null

if (-not $ecrUri) {
    $ecrUri = aws ecr create-repository `
        --repository-name "$($config.ProjectName)/api" `
        --image-scanning-configuration scanOnPush=true `
        --query 'repository.repositoryUri' `
        --output text
    Write-Host "  ✓ ECR repository created: $ecrUri" -ForegroundColor Green
} else {
    Write-Host "  ✓ ECR repository exists: $ecrUri" -ForegroundColor Green
}

# Step 7: Build and Push Docker Image
if (-not $SkipImageBuild) {
    Write-Host "`n[8/12] Building and pushing Docker image..." -ForegroundColor Yellow
    
    # Ensure we're in the project root directory for Docker build
    $projectRoot = Split-Path -Parent $PSScriptRoot
    Push-Location $projectRoot
    
    Write-Host "  → Authenticating to ECR..." -ForegroundColor Cyan
    aws ecr get-login-password --region $config.Region | docker login --username AWS --password-stdin "$($config.AccountId).dkr.ecr.$($config.Region).amazonaws.com"
    
    if (-not $PushOnly) {
        Write-Host "  → Building Docker image..." -ForegroundColor Cyan
        docker build -f Dockerfile.api -t "$($config.ProjectName)-api:latest" .
    } else {
        Write-Host "  → Skipping build, using existing local image: $($config.ProjectName)-api:latest" -ForegroundColor Cyan
    }
    
    Write-Host "  → Tagging image..." -ForegroundColor Cyan
    docker tag "$($config.ProjectName)-api:latest" "${ecrUri}:latest"
    
    Write-Host "  → Pushing to ECR (this may take a few minutes)..." -ForegroundColor Cyan
    docker push "${ecrUri}:latest"
    
    Pop-Location
    Write-Host "  ✓ Docker image pushed to ECR" -ForegroundColor Green
} else {
    Write-Host "`n[8/12] Skipping Docker image build and push (--SkipImageBuild)" -ForegroundColor Yellow
}

# Step 8: Create Application Load Balancer
Write-Host "`n[9/12] Creating Application Load Balancer..." -ForegroundColor Yellow

$albArn = aws elbv2 describe-load-balancers `
    --names "$($config.ProjectName)-alb" `
    --query 'LoadBalancers[0].LoadBalancerArn' `
    --output text 2>$null

if (-not $albArn -or $albArn -eq "None") {
    $albArn = aws elbv2 create-load-balancer `
        --name "$($config.ProjectName)-alb" `
        --subnets $subnet1 $subnet2 `
        --security-groups $albSgId `
        --scheme internet-facing `
        --type application `
        --ip-address-type ipv4 `
        --query 'LoadBalancers[0].LoadBalancerArn' `
        --output text
    Write-Host "  ✓ ALB created: $albArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ ALB already exists: $albArn" -ForegroundColor Green
}

$albDns = aws elbv2 describe-load-balancers `
    --load-balancer-arns $albArn `
    --query 'LoadBalancers[0].DNSName' `
    --output text

# Create Target Group
$tgArn = aws elbv2 describe-target-groups `
    --names "$($config.ProjectName)-tg" `
    --query 'TargetGroups[0].TargetGroupArn' `
    --output text 2>$null

if (-not $tgArn -or $tgArn -eq "None") {
    $tgArn = aws elbv2 create-target-group `
        --name "$($config.ProjectName)-tg" `
        --protocol HTTP `
        --port 8000 `
        --vpc-id $config.VpcId `
        --target-type ip `
        --health-check-enabled `
        --health-check-path "/health" `
        --health-check-interval-seconds 30 `
        --health-check-timeout-seconds 5 `
        --healthy-threshold-count 2 `
        --unhealthy-threshold-count 3 `
        --query 'TargetGroups[0].TargetGroupArn' `
        --output text
    Write-Host "  ✓ Target Group created: $tgArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ Target Group exists: $tgArn" -ForegroundColor Green
}

# Create Listener
$listenerArn = aws elbv2 describe-listeners `
    --load-balancer-arn $albArn `
    --query 'Listeners[0].ListenerArn' `
    --output text 2>$null

if (-not $listenerArn -or $listenerArn -eq "None") {
    aws elbv2 create-listener `
        --load-balancer-arn $albArn `
        --protocol HTTP `
        --port 80 `
        --default-actions "Type=forward,TargetGroupArn=$tgArn" | Out-Null
    Write-Host "  ✓ Listener created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Listener already exists" -ForegroundColor Green
}

# Step 9: Create ECS Cluster
Write-Host "`n[10/12] Creating ECS cluster..." -ForegroundColor Yellow

$clusterArn = aws ecs describe-clusters `
    --clusters "$($config.ProjectName)-cluster" `
    --query 'clusters[0].clusterArn' `
    --output text 2>$null

if (-not $clusterArn -or $clusterArn -eq "None") {
    $clusterArn = aws ecs create-cluster `
        --cluster-name "$($config.ProjectName)-cluster" `
        --query 'cluster.clusterArn' `
        --output text
    Write-Host "  ✓ ECS cluster created: $clusterArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ ECS cluster exists: $clusterArn" -ForegroundColor Green
}

# Step 10: Register Task Definition
Write-Host "`n[11/12] Registering ECS task definition..." -ForegroundColor Yellow

$taskDef = @{
    family = "$($config.ProjectName)-api"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = $config.ECSTaskCPU
    memory = $config.ECSTaskMemory
    executionRoleArn = $taskExecRoleArn
    taskRoleArn = $taskRoleArn
    containerDefinitions = @(
        @{
            name = "$($config.ProjectName)-api"
            image = "${ecrUri}:latest"
            essential = $true
            portMappings = @(
                @{
                    containerPort = 8000
                    protocol = "tcp"
                }
            )
            environment = @(
                @{ name = "API_HOST"; value = "0.0.0.0" }
                @{ name = "API_PORT"; value = "8000" }
                @{ name = "AWS_REGION"; value = $config.Region }
            )
            secrets = @(
                @{ name = "DATABASE_URL"; valueFrom = "${secretArn}:DATABASE_URL::" }
                @{ name = "AUTH0_DOMAIN"; valueFrom = "${secretArn}:AUTH0_DOMAIN::" }
                @{ name = "AUTH0_CLIENT_ID"; valueFrom = "${secretArn}:AUTH0_CLIENT_ID::" }
                @{ name = "AUTH0_CLIENT_SECRET"; valueFrom = "${secretArn}:AUTH0_CLIENT_SECRET::" }
                @{ name = "AUTH0_API_AUDIENCE"; valueFrom = "${secretArn}:AUTH0_API_AUDIENCE::" }
                @{ name = "S3_BUCKET_NAME"; valueFrom = "${secretArn}:S3_BUCKET_NAME::" }
                @{ name = "AWS_ACCESS_KEY_ID"; valueFrom = "${secretArn}:AWS_ACCESS_KEY_ID::" }
                @{ name = "AWS_SECRET_ACCESS_KEY"; valueFrom = "${secretArn}:AWS_SECRET_ACCESS_KEY::" }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = "/ecs/$($config.ProjectName)-api"
                    "awslogs-region" = $config.Region
                    "awslogs-stream-prefix" = "ecs"
                }
            }
            healthCheck = @{
                command = @("CMD-SHELL", "curl -f http://localhost:8000/health || exit 1")
                interval = 30
                timeout = 10
                retries = 5
                startPeriod = 120
            }
        }
    )
} | ConvertTo-Json -Depth 10

$taskDefArn = aws ecs register-task-definition `
    --cli-input-json $taskDef `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

Write-Host "  ✓ Task definition registered: $taskDefArn" -ForegroundColor Green

# Step 11: Create ECS Service
Write-Host "`n[12/12] Creating ECS service..." -ForegroundColor Yellow

$serviceArn = aws ecs describe-services `
    --cluster "$($config.ProjectName)-cluster" `
    --services "$($config.ProjectName)-api-service" `
    --query 'services[0].serviceArn' `
    --output text 2>$null

if (-not $serviceArn -or $serviceArn -eq "None") {
    $serviceArn = aws ecs create-service `
        --cluster "$($config.ProjectName)-cluster" `
        --service-name "$($config.ProjectName)-api-service" `
        --task-definition "$($config.ProjectName)-api" `
        --desired-count $config.ECSDesiredCount `
        --launch-type FARGATE `
        --platform-version LATEST `
        --network-configuration "awsvpcConfiguration={subnets=[$subnet1,$subnet2],securityGroups=[$ecsSgId],assignPublicIp=ENABLED}" `
        --load-balancers "targetGroupArn=$tgArn,containerName=$($config.ProjectName)-api,containerPort=8000" `
        --health-check-grace-period-seconds 120 `
        --query 'service.serviceArn' `
        --output text
    
    Write-Host "  ✓ ECS service created: $serviceArn" -ForegroundColor Green
    Write-Host "  → Waiting for service to stabilize (this takes 5-10 minutes)..." -ForegroundColor Cyan
    aws ecs wait services-stable --cluster "$($config.ProjectName)-cluster" --services "$($config.ProjectName)-api-service"
} else {
    Write-Host "  ✓ ECS service exists: $serviceArn" -ForegroundColor Green
    Write-Host "  → Updating service with new task definition..." -ForegroundColor Cyan
    aws ecs update-service `
        --cluster "$($config.ProjectName)-cluster" `
        --service "$($config.ProjectName)-api-service" `
        --task-definition "$($config.ProjectName)-api" `
        --force-new-deployment | Out-Null
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Endpoint: http://$albDns" -ForegroundColor Cyan
Write-Host "Health Check: http://$albDns/health" -ForegroundColor Cyan
Write-Host "Swagger Docs: http://$albDns/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "RDS Endpoint: $rdsEndpoint" -ForegroundColor Yellow
Write-Host "RDS Password: $($config.RDSMasterPassword)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "1. Wait 5-10 minutes for ECS tasks to start" -ForegroundColor White
Write-Host "2. Check health: curl http://$albDns/health" -ForegroundColor White
Write-Host "3. Initialize database (connect via ECS task or bastion)" -ForegroundColor White
Write-Host "4. Run: python init_db.py" -ForegroundColor White
Write-Host "5. Run: python populate_sample_data.py" -ForegroundColor White
Write-Host ""
Write-Host "Monitor logs: aws logs tail /ecs/$($config.ProjectName)-api --follow" -ForegroundColor White
Write-Host ""

# Save deployment info to file
$deploymentInfo = @{
    DeploymentDate = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Region = $config.Region
    VpcId = $config.VpcId
    ALBSecurityGroup = $albSgId
    ECSSecurityGroup = $ecsSgId
    RDSSecurityGroup = $rdsSgId
    RDSEndpoint = $rdsEndpoint
    RDSPassword = $config.RDSMasterPassword
    SecretArn = $secretArn
    TaskExecutionRoleArn = $taskExecRoleArn
    TaskRoleArn = $taskRoleArn
    ECRRepository = $ecrUri
    ALBEndpoint = $albDns
    ALBArn = $albArn
    TargetGroupArn = $tgArn
    ECSCluster = $clusterArn
    ECSService = $serviceArn
    TaskDefinition = $taskDefArn
} | ConvertTo-Json

$deploymentInfo | Out-File "$PSScriptRoot/deployment-info.json"
Write-Host "Deployment info saved to: $PSScriptRoot/deployment-info.json" -ForegroundColor Gray
