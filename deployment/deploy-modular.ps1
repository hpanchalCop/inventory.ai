# Inventory.AI Modular AWS Deployment Script
# Automated deployment to ECS Fargate with RDS PostgreSQL

param(
    [string]$ConfigFile = "$PSScriptRoot/config.json",
    [string]$Region,
    [string]$AccountId,
    [string]$VpcId,
    [switch]$SkipImageBuild,
    [switch]$PushOnly,
    [switch]$ApiOnly,
    [switch]$DashboardOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Inventory.AI Modular Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load configuration from JSON
Write-Host "Loading configuration from: $ConfigFile" -ForegroundColor Yellow
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file not found: $ConfigFile"
    exit 1
}

$config = Get-Content $ConfigFile | ConvertFrom-Json

# Override with command-line parameters if provided
if ($Region) { $config.region = $Region }
if ($AccountId) { $config.accountId = $AccountId }
if ($VpcId) { $config.vpcId = $VpcId }

# Helper function to replace placeholders in JSON
function Replace-Placeholders {
    param(
        [string]$JsonContent,
        [hashtable]$Replacements
    )
    
    $result = $JsonContent
    foreach ($key in $Replacements.Keys) {
        $result = $result -replace "{{$key}}", $Replacements[$key]
    }
    return $result
}

# Helper function to deploy a service (API or Dashboard)
function Deploy-Service {
    param(
        [string]$ServiceName,
        [string]$DockerfilePath,
        [int]$ContainerPort,
        [string]$TaskDefPath,
        [string]$HealthCheckPath,
        [PSCustomObject]$ServiceConfig
    )
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Deploying $ServiceName Service" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    $serviceLower = $ServiceName.ToLower()
    $ecrRepoName = "$($config.projectName)/$serviceLower"
    $logGroupName = "/ecs/$($config.projectName)-$serviceLower"
    
    # Create CloudWatch Log Group
    Write-Host "`n[$ServiceName] Creating CloudWatch log group..." -ForegroundColor Yellow
    aws logs create-log-group --log-group-name $logGroupName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Log group created: $logGroupName" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Log group already exists: $logGroupName" -ForegroundColor Green
    }
    
    aws logs put-retention-policy `
        --log-group-name $logGroupName `
        --retention-in-days $config.logging.retentionDays | Out-Null
    
    # Create ECR Repository
    Write-Host "`n[$ServiceName] Creating ECR repository..." -ForegroundColor Yellow
    $ecrUri = aws ecr describe-repositories `
        --repository-names $ecrRepoName `
        --query 'repositories[0].repositoryUri' `
        --output text 2>$null
    
    if (-not $ecrUri) {
        $ecrUri = aws ecr create-repository `
            --repository-name $ecrRepoName `
            --image-scanning-configuration scanOnPush=true `
            --query 'repository.repositoryUri' `
            --output text
        Write-Host "  ✓ ECR repository created: $ecrUri" -ForegroundColor Green
    } else {
        Write-Host "  ✓ ECR repository exists: $ecrUri" -ForegroundColor Green
    }
    
    # Build and Push Docker Image
    if (-not $SkipImageBuild) {
        Write-Host "`n[$ServiceName] Building and pushing Docker image..." -ForegroundColor Yellow
        
        $projectRoot = Split-Path -Parent $PSScriptRoot
        Push-Location $projectRoot
        
        Write-Host "  → Authenticating to ECR..." -ForegroundColor Cyan
        aws ecr get-login-password --region $config.region | `
            docker login --username AWS --password-stdin "$($config.accountId).dkr.ecr.$($config.region).amazonaws.com"
        
        if (-not $PushOnly) {
            Write-Host "  → Building Docker image..." -ForegroundColor Cyan
            $imageName = "$($config.projectName)-$serviceLower"
            Write-Host "  → Image name: $imageName" -ForegroundColor Cyan
            docker build -f $DockerfilePath -t "${imageName}:latest" .
        } else {
            Write-Host "  → Skipping build, using existing local image" -ForegroundColor Cyan
        }
        
        $imageName = "$($config.projectName)-$serviceLower"
        Write-Host "  → Tagging image..." -ForegroundColor Cyan
        docker tag "${imageName}:latest" "${ecrUri}:latest"
        
        Write-Host "  → Pushing to ECR..." -ForegroundColor Cyan
        docker push "${ecrUri}:latest"
        
        Pop-Location
        Write-Host "  ✓ Docker image pushed to ECR" -ForegroundColor Green
    } else {
        Write-Host "`n[$ServiceName] Skipping Docker image build and push" -ForegroundColor Yellow
    }
    
    # Register Task Definition
    Write-Host "`n[$ServiceName] Registering ECS task definition..." -ForegroundColor Yellow
    
    $taskDefJson = Get-Content $TaskDefPath -Raw
    $replacements = @{
        ECSTaskCPU = $ServiceConfig.taskCpu
        ECSTaskMemory = $ServiceConfig.taskMemory
        TaskExecutionRoleArn = $script:taskExecRoleArn
        TaskRoleArn = $script:taskRoleArn
        ECRImageUri = "${ecrUri}:latest"
        SecretArn = $script:secretArn
        Region = $config.region
        ApiUrl = "http://$script:albDns"
        DashboardUrl = "http://$script:albDns/dashboard"
    }
    
    $taskDefJson = Replace-Placeholders -JsonContent $taskDefJson -Replacements $replacements
    
    $taskDefArn = aws ecs register-task-definition `
        --cli-input-json $taskDefJson `
        --query 'taskDefinition.taskDefinitionArn' `
        --output text
    
    Write-Host "  ✓ Task definition registered: $taskDefArn" -ForegroundColor Green
    
    # Create Target Group
    Write-Host "`n[$ServiceName] Creating target group..." -ForegroundColor Yellow
    $tgName = "$($config.projectName)-$serviceLower-tg"
    
    $tgArn = aws elbv2 describe-target-groups `
        --names $tgName `
        --query 'TargetGroups[0].TargetGroupArn' `
        --output text 2>$null
    
    if (-not $tgArn -or $tgArn -eq "None") {
        $tgArn = aws elbv2 create-target-group `
            --name $tgName `
            --protocol HTTP `
            --port $ContainerPort `
            --vpc-id $config.vpcId `
            --target-type ip `
            --health-check-enabled `
            --health-check-path $HealthCheckPath `
            --health-check-interval-seconds $ServiceConfig.healthCheck.interval `
            --health-check-timeout-seconds $ServiceConfig.healthCheck.timeout `
            --healthy-threshold-count 2 `
            --unhealthy-threshold-count 3 `
            --query 'TargetGroups[0].TargetGroupArn' `
            --output text
        Write-Host "  ✓ Target Group created: $tgArn" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Target Group exists: $tgArn" -ForegroundColor Green
    }
    
    # Create or Update Listener Rule
    if ($ServiceName -eq "Dashboard") {
        Write-Host "`n[$ServiceName] Creating ALB listener rule..." -ForegroundColor Yellow
        
        # Get existing rules
        $rules = aws elbv2 describe-rules `
            --listener-arn $script:listenerArn `
            --query 'Rules[?!IsDefault]' `
            --output json | ConvertFrom-Json
        
        $dashboardRule = $rules | Where-Object { 
            $_.Conditions[0].PathPatternConfig.Values -contains "/dashboard*" 
        }
        
        if (-not $dashboardRule) {
            $priority = 10
            aws elbv2 create-rule `
                --listener-arn $script:listenerArn `
                --priority $priority `
                --conditions "Field=path-pattern,Values='/dashboard*'" `
                --actions "Type=forward,TargetGroupArn=$tgArn" | Out-Null
            Write-Host "  ✓ Listener rule created for /dashboard* path" -ForegroundColor Green
        } else {
            Write-Host "  ✓ Listener rule already exists" -ForegroundColor Green
        }
    }
    
    # Create ECS Service
    Write-Host "`n[$ServiceName] Creating ECS service..." -ForegroundColor Yellow
    $serviceName = "$($config.projectName)-$serviceLower-service"
    
    $serviceArn = aws ecs describe-services `
        --cluster "$($config.projectName)-cluster" `
        --services $serviceName `
        --query 'services[0].serviceArn' `
        --output text 2>$null
    
    if (-not $serviceArn -or $serviceArn -eq "None") {
        $serviceArn = aws ecs create-service `
            --cluster "$($config.projectName)-cluster" `
            --service-name $serviceName `
            --task-definition "$($config.projectName)-$serviceLower" `
            --desired-count $ServiceConfig.desiredCount `
            --launch-type FARGATE `
            --platform-version LATEST `
            --network-configuration "awsvpcConfiguration={subnets=[$($script:subnet1),$($script:subnet2)],securityGroups=[$($script:ecsSgId)],assignPublicIp=ENABLED}" `
            --load-balancers "targetGroupArn=$tgArn,containerName=$($config.projectName)-$serviceLower,containerPort=$ContainerPort" `
            --health-check-grace-period-seconds $ServiceConfig.healthCheck.startPeriod `
            --query 'service.serviceArn' `
            --output text
        
        Write-Host "  ✓ ECS service created: $serviceArn" -ForegroundColor Green
    } else {
        Write-Host "  ✓ ECS service exists, updating..." -ForegroundColor Green
        aws ecs update-service `
            --cluster "$($config.projectName)-cluster" `
            --service $serviceName `
            --task-definition "$($config.projectName)-$serviceLower" `
            --force-new-deployment | Out-Null
    }
    
    return @{
        ServiceArn = $serviceArn
        TaskDefArn = $taskDefArn
        TargetGroupArn = $tgArn
        ECRUri = $ecrUri
    }
}

# ============================================
# Main Deployment Flow
# ============================================

# Get VPC Subnets
Write-Host "`n[1/10] Getting VPC subnets..." -ForegroundColor Yellow
$subnets = aws ec2 describe-subnets `
    --filters "Name=vpc-id,Values=$($config.vpcId)" `
    --query 'Subnets[?MapPublicIpOnLaunch==`true`].[SubnetId,AvailabilityZone]' `
    --output json | ConvertFrom-Json

$subnet1 = $subnets[0][0]
$subnet2 = $subnets[1][0]
$az1 = $subnets[0][1]
$az2 = $subnets[1][1]

Write-Host "  ✓ Using subnets: $subnet1 ($az1), $subnet2 ($az2)" -ForegroundColor Green

# Create Security Groups
Write-Host "`n[2/10] Creating Security Groups..." -ForegroundColor Yellow

# ALB Security Group
$albSgId = aws ec2 create-security-group `
    --group-name "$($config.projectName)-alb-sg" `
    --description "Security group for ALB" `
    --vpc-id $config.vpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $albSgId) {
    $albSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.projectName)-alb-sg" "Name=vpc-id,Values=$($config.vpcId)" `
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
    --group-name "$($config.projectName)-ecs-sg" `
    --description "Security group for ECS tasks" `
    --vpc-id $config.vpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $ecsSgId) {
    $ecsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.projectName)-ecs-sg" "Name=vpc-id,Values=$($config.vpcId)" `
        --query 'SecurityGroups[0].GroupId' `
        --output text
    Write-Host "  ✓ ECS Security Group already exists: $ecsSgId" -ForegroundColor Green
    
    # Ensure required ports are open (ignore errors if rules already exist)
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol tcp `
        --port 8000 `
        --source-group $albSgId 2>$null | Out-Null
    
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol tcp `
        --port 8050 `
        --source-group $albSgId 2>$null | Out-Null
    
    Write-Host "  ✓ Verified security group rules for ports 8000 and 8050" -ForegroundColor Green
} else {
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol tcp `
        --port 8000 `
        --source-group $albSgId | Out-Null
    
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol tcp `
        --port 8050 `
        --source-group $albSgId | Out-Null
    
    aws ec2 authorize-security-group-ingress `
        --group-id $ecsSgId `
        --protocol -1 `
        --source-group $ecsSgId | Out-Null
    Write-Host "  ✓ Created ECS Security Group: $ecsSgId" -ForegroundColor Green
}

# RDS Security Group
$rdsSgId = aws ec2 create-security-group `
    --group-name "$($config.projectName)-rds-sg" `
    --description "Security group for RDS" `
    --vpc-id $config.vpcId `
    --query 'GroupId' `
    --output text 2>$null

if (-not $rdsSgId) {
    $rdsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=$($config.projectName)-rds-sg" "Name=vpc-id,Values=$($config.vpcId)" `
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

# Create RDS PostgreSQL Instance
Write-Host "`n[3/10] Creating RDS PostgreSQL instance..." -ForegroundColor Yellow

$rdsExists = aws rds describe-db-instances `
    --db-instance-identifier "$($config.projectName)-db" `
    --query 'DBInstances[0].DBInstanceStatus' `
    --output text 2>$null

if ($rdsExists) {
    Write-Host "  ✓ RDS instance already exists (Status: $rdsExists)" -ForegroundColor Green
    $rdsEndpoint = aws rds describe-db-instances `
        --db-instance-identifier "$($config.projectName)-db" `
        --query 'DBInstances[0].Endpoint.Address' `
        --output text
} else {
    aws rds create-db-subnet-group `
        --db-subnet-group-name "$($config.projectName)-db-subnet-group" `
        --db-subnet-group-description "Subnet group for $($config.projectName)" `
        --subnet-ids $subnet1 $subnet2 2>$null | Out-Null
    
    Write-Host "  → Creating RDS instance (this takes 5-10 minutes)..." -ForegroundColor Cyan
    aws rds create-db-instance `
        --db-instance-identifier "$($config.projectName)-db" `
        --db-instance-class $config.database.instanceClass `
        --engine $config.database.engine `
        --engine-version $config.database.engineVersion `
        --master-username $config.database.masterUsername `
        --master-user-password $config.database.masterPassword `
        --allocated-storage $config.database.allocatedStorage `
        --db-subnet-group-name "$($config.projectName)-db-subnet-group" `
        --vpc-security-group-ids $rdsSgId `
        --db-name $config.database.dbName `
        --backup-retention-period $config.database.backupRetentionPeriod `
        --storage-encrypted `
        --no-publicly-accessible | Out-Null
    
    Write-Host "  → Waiting for RDS to become available..." -ForegroundColor Cyan
    aws rds wait db-instance-available --db-instance-identifier "$($config.projectName)-db"
    
    $rdsEndpoint = aws rds describe-db-instances `
        --db-instance-identifier "$($config.projectName)-db" `
        --query 'DBInstances[0].Endpoint.Address' `
        --output text
    
    Write-Host "  ✓ RDS instance created: $rdsEndpoint" -ForegroundColor Green
}

$databaseUrl = "postgresql://$($config.database.masterUsername):$($config.database.masterPassword)@${rdsEndpoint}:5432/$($config.database.dbName)?sslmode=require"

# Create Secrets Manager Secret
Write-Host "`n[4/10] Creating Secrets Manager secret..." -ForegroundColor Yellow

$secretString = @{
    DATABASE_URL = $databaseUrl
    AUTH0_DOMAIN = $config.auth0.domain
    AUTH0_CLIENT_ID = $config.auth0.clientId
    AUTH0_CLIENT_SECRET = $config.auth0.clientSecret
    AUTH0_API_AUDIENCE = $config.auth0.apiAudience
    AWS_ACCESS_KEY_ID = $config.aws.accessKeyId
    AWS_SECRET_ACCESS_KEY = $config.aws.secretAccessKey
    S3_BUCKET_NAME = $config.aws.s3BucketName
} | ConvertTo-Json -Compress

$secretArn = aws secretsmanager create-secret `
    --name "$($config.projectName)/prod/env" `
    --description "Production environment variables for $($config.projectName)" `
    --secret-string $secretString `
    --query 'ARN' `
    --output text 2>$null

if (-not $secretArn) {
    $secretArn = aws secretsmanager describe-secret `
        --secret-id "$($config.projectName)/prod/env" `
        --query 'ARN' `
        --output text
    
    aws secretsmanager update-secret `
        --secret-id "$($config.projectName)/prod/env" `
        --secret-string $secretString | Out-Null
    
    Write-Host "  ✓ Secret updated: $secretArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ Secret created: $secretArn" -ForegroundColor Green
}

# Create IAM Roles
Write-Host "`n[5/10] Creating IAM roles..." -ForegroundColor Yellow

# Task Execution Role
$taskExecRoleName = "$($config.projectName)-ecs-task-execution-role"
$taskExecRoleArn = aws iam get-role --role-name $taskExecRoleName --query 'Role.Arn' --output text 2>$null

if (-not $taskExecRoleArn) {
    $trustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "ecs-tasks.amazonaws.com" }
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
$taskRoleName = "$($config.projectName)-ecs-task-role"
$taskRoleArn = aws iam get-role --role-name $taskRoleName --query 'Role.Arn' --output text 2>$null

if (-not $taskRoleArn) {
    $trustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "ecs-tasks.amazonaws.com" }
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
                Resource = @("arn:aws:s3:::$($config.aws.s3BucketName)", "arn:aws:s3:::$($config.aws.s3BucketName)/*")
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

# Create Application Load Balancer
Write-Host "`n[6/10] Creating Application Load Balancer..." -ForegroundColor Yellow

$albArn = aws elbv2 describe-load-balancers `
    --names "$($config.projectName)-alb" `
    --query 'LoadBalancers[0].LoadBalancerArn' `
    --output text 2>$null

if (-not $albArn -or $albArn -eq "None") {
    $albArn = aws elbv2 create-load-balancer `
        --name "$($config.projectName)-alb" `
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

# Create Default Listener (will be configured per service)
$listenerArn = aws elbv2 describe-listeners `
    --load-balancer-arn $albArn `
    --query 'Listeners[0].ListenerArn' `
    --output text 2>$null

if (-not $listenerArn -or $listenerArn -eq "None") {
    # Will create with API target group as default
    Write-Host "  ✓ Listener will be created with API service" -ForegroundColor Green
} else {
    Write-Host "  ✓ Listener already exists: $listenerArn" -ForegroundColor Green
}

# Create ECS Cluster
Write-Host "`n[7/10] Creating ECS cluster..." -ForegroundColor Yellow

$clusterArn = aws ecs describe-clusters `
    --clusters "$($config.projectName)-cluster" `
    --query 'clusters[0].clusterArn' `
    --output text 2>$null

if (-not $clusterArn -or $clusterArn -eq "None") {
    $clusterArn = aws ecs create-cluster `
        --cluster-name "$($config.projectName)-cluster" `
        --query 'cluster.clusterArn' `
        --output text
    Write-Host "  ✓ ECS cluster created: $clusterArn" -ForegroundColor Green
} else {
    Write-Host "  ✓ ECS cluster exists: $clusterArn" -ForegroundColor Green
}

# Deploy Services
$deploymentResults = @{}

if (-not $DashboardOnly) {
    Write-Host "`n[8/10] Deploying API Service..." -ForegroundColor Yellow
    $apiResult = Deploy-Service `
        -ServiceName "API" `
        -DockerfilePath "Dockerfile.api" `
        -ContainerPort $config.ecs.api.containerPort `
        -TaskDefPath "$PSScriptRoot/task-definition-api.json" `
        -HealthCheckPath $config.ecs.api.healthCheckPath `
        -ServiceConfig $config.ecs.api
    
    $deploymentResults.API = $apiResult
    
    # Create default listener with API target group
    if (-not $listenerArn -or $listenerArn -eq "None") {
        Write-Host "`nCreating ALB default listener..." -ForegroundColor Yellow
        $listenerArn = aws elbv2 create-listener `
            --load-balancer-arn $albArn `
            --protocol HTTP `
            --port 80 `
            --default-actions "Type=forward,TargetGroupArn=$($apiResult.TargetGroupArn)" `
            --query 'Listeners[0].ListenerArn' `
            --output text
        Write-Host "  ✓ Default listener created" -ForegroundColor Green
    }
}

if (-not $ApiOnly) {
    Write-Host "`n[9/10] Deploying Dashboard Service..." -ForegroundColor Yellow
    $dashboardResult = Deploy-Service `
        -ServiceName "Dashboard" `
        -DockerfilePath "Dockerfile.dashboard" `
        -ContainerPort $config.ecs.dashboard.containerPort `
        -TaskDefPath "$PSScriptRoot/task-definition-dashboard.json" `
        -HealthCheckPath $config.ecs.dashboard.healthCheckPath `
        -ServiceConfig $config.ecs.dashboard
    
    $deploymentResults.Dashboard = $dashboardResult
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URLs:" -ForegroundColor Cyan
Write-Host "  API Endpoint:       http://$albDns" -ForegroundColor White
Write-Host "  API Health:         http://$albDns/health" -ForegroundColor White
Write-Host "  API Docs:           http://$albDns/docs" -ForegroundColor White

if (-not $ApiOnly) {
    Write-Host "  Dashboard:          http://$albDns/dashboard" -ForegroundColor White
}

Write-Host ""
Write-Host "Infrastructure:" -ForegroundColor Cyan
Write-Host "  RDS Endpoint:       $rdsEndpoint" -ForegroundColor White
Write-Host "  RDS Password:       $($config.database.masterPassword)" -ForegroundColor White
Write-Host "  ECS Cluster:        $($config.projectName)-cluster" -ForegroundColor White
Write-Host ""
Write-Host "Monitoring:" -ForegroundColor Cyan
Write-Host "  API Logs:           aws logs tail /ecs/$($config.projectName)-api --follow" -ForegroundColor Gray
if (-not $ApiOnly) {
    Write-Host "  Dashboard Logs:     aws logs tail /ecs/$($config.projectName)-dashboard --follow" -ForegroundColor Gray
}
Write-Host ""

# Save deployment info
$deploymentInfo = @{
    DeploymentDate = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Region = $config.region
    VpcId = $config.vpcId
    ALBSecurityGroup = $albSgId
    ECSSecurityGroup = $ecsSgId
    RDSSecurityGroup = $rdsSgId
    RDSEndpoint = $rdsEndpoint
    RDSPassword = $config.database.masterPassword
    SecretArn = $secretArn
    TaskExecutionRoleArn = $taskExecRoleArn
    TaskRoleArn = $taskRoleArn
    ALBEndpoint = $albDns
    ALBArn = $albArn
    ListenerArn = $listenerArn
    ECSCluster = $clusterArn
    Services = $deploymentResults
} | ConvertTo-Json -Depth 10

$deploymentInfo | Out-File "$PSScriptRoot/deployment-info.json"
Write-Host "Deployment info saved to: $PSScriptRoot/deployment-info.json" -ForegroundColor Gray
Write-Host ""
