# inventory.ai

**AI-powered inventory management system** with multimodal embeddings, semantic search, and enterprise-grade security. Deployed on AWS ECS Fargate with Auth0 authentication.

🔗 **Live API**: http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com

## Features

### 🔐 Security & Authentication
- **Auth0 Integration**: Enterprise-grade authentication with JWT tokens
- **Role-Based Access**: Protected admin endpoints for sensitive operations
- **Secure Secrets**: AWS Secrets Manager integration
- **Environment-Based Config**: No hardcoded credentials

### 🚀 FastAPI Microservice
- **Multipart Requests**: Support for image + text product uploads
- **Text-Only Support**: Create products with descriptions only
- **Multimodal Embeddings**: Combined image + text embeddings using CLIP for enhanced product matching
- **Advanced Search**: Text-based semantic search, image similarity search, and multimodal search
- **RESTful API**: Complete CRUD operations for product management
- **Health Monitoring**: Health check endpoints with database connectivity verification
- **Admin Stats**: Real-time API usage statistics and CloudWatch metrics

### 💾 Storage & Database
- **AWS S3**: Scalable storage for product images and ML metadata
- **PostgreSQL + pgvector**: Vector embeddings for efficient similarity search
- **Amazon RDS**: Managed PostgreSQL database with encryption
- **CloudWatch Logs**: Centralized logging and monitoring

### 📊 Plotly Dash Admin Dashboard
- **Product Management**: Add, view, and manage products through an intuitive web interface
- **Analytics Dashboard**: Visualize product distribution by category and price
- **Real-time Stats**: Monitor total products, categories, and API usage
- **CloudWatch Integration**: View API metrics and logs
- **Auth0 Login**: Secure authentication for admin access
- **Auto-refresh**: Dashboard updates automatically every 30 seconds

### ☁️ AWS Cloud Infrastructure
- **ECS Fargate**: Serverless container orchestration
- **Application Load Balancer**: High availability and traffic distribution
- **Auto-scaling**: Automatic scaling based on demand
- **Multi-AZ Deployment**: High availability across availability zones
- **IAM Roles**: Secure service-to-service authentication
- **VPC Security Groups**: Network isolation and security

## Architecture

```
inventory.ai/
├── api/                    # FastAPI microservice
│   └── main.py            # API endpoints and business logic
├── dashboard/             # Plotly Dash admin interface
│   └── app.py            # Dashboard application
├── shared/                # Shared modules
│   ├── auth.py           # Auth0 authentication & JWT verification
│   ├── cloudwatch_stats.py # CloudWatch metrics integration
│   ├── config.py         # Configuration management
│   ├── database.py       # Database models and setup
│   ├── ml_service.py     # ML embeddings service (CLIP + MiniLM)
│   └── s3_service.py     # AWS S3 integration
├── deployment/            # AWS deployment configurations
│   ├── config.json       # Deployment configuration (gitignored)
│   ├── config.example.json # Config template
│   ├── deploy-modular.ps1 # Modular deployment script
│   ├── task-definition-api.json
│   ├── task-definition-dashboard.json
│   └── deployment-info.json # Deployment state
├── tests/                 # Test suite
│   ├── test_api.py       # API integration tests
│   └── test_ml_service.py # ML service unit tests
├── Dockerfile.api         # API container definition
├── Dockerfile.dashboard   # Dashboard container definition
├── docker-compose.yml     # Local development setup
├── requirements.txt       # API dependencies
└── requirements-dashboard.txt # Dashboard dependencies
```

### AWS Infrastructure

```
┌─────────────────────────────────────────────────────────┐
│                  Application Load Balancer              │
│  inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   ┌────▼────┐      ┌────▼────┐
   │  API    │      │Dashboard│
   │ Service │      │ Service │
   │ (ECS)   │      │  (ECS)  │
   └────┬────┘      └────┬────┘
        │                │
        ├────────┬───────┤
        │        │       │
   ┌────▼────┐ ┌▼──┐ ┌──▼─────┐
   │   RDS   │ │S3 │ │Auth0   │
   │Postgres │ │   │ │        │
   └─────────┘ └───┘ └────────┘
```

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- PostgreSQL with pgvector extension
- AWS Account (for S3 and ECS deployment)

## Quick Start

### Local Development with Docker Compose

1. **Clone the repository**:
```bash
git clone https://github.com/hpanchalCop/inventory.ai.git
cd inventory.ai
```

2. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your AWS credentials and other settings
```

3. **Start the services**:
```bash
docker-compose up -d
```

4. **Access the services**:
- FastAPI: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Dashboard: http://localhost:8050

### Manual Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up PostgreSQL with pgvector**:
```bash
# Install pgvector extension in your PostgreSQL database
CREATE EXTENSION vector;
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start the API**:
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

5. **Start the Dashboard** (in a new terminal):
```bash
python dashboard/app.py
```

## API Endpoints

### Products

- `POST /products/multipart` - Create product with image and text (requires Auth0 token)
  - Form fields: `name`, `description`, `category`, `price`, `image` (file)
  
- `POST /products/text-only` - Create product with text only (requires Auth0 token)
  - JSON body: `{"name": "...", "description": "...", "category": "...", "price": 0.0}`

- `GET /products` - List all products
  - Query params: `skip`, `limit`, `category`

- `GET /products/{product_id}` - Get specific product

- `DELETE /products/{product_id}` - Delete product (requires Auth0 token)

### Search

- `POST /search/text` - Text-based semantic search
  - JSON body: `{"query": "search term", "top_k": 5}`
  - Returns products ranked by text similarity

- `POST /search/image` - Image-based similarity search
  - Form data: `image` (file), `top_k` (optional)
  - Returns visually similar products

- `POST /search/multimodal` - Combined text+image search
  - JSON body: `{"product_id": 1, "top_k": 5}`
  - Uses both text and image embeddings

### Admin & Monitoring

- `GET /admin/stats` - API usage statistics (requires Auth0 token with admin role)
  - Returns request counts, CloudWatch metrics, and system stats

- `GET /admin/stats/summary` - Summary statistics
  - Product counts, embeddings info, and storage metrics

### Health & Info

- `GET /` - API information and available endpoints
- `GET /health` - Health check with database connectivity
- `GET /auth/me` - Current user info (requires Auth0 token)

## API Usage Examples

### Authentication

Get an Auth0 token first:
```python
# Use the included get_token.py script
import subprocess
token = subprocess.check_output(['python', 'get_token.py']).decode().strip()
```

### Create Product with Image (cURL)
```bash
# Get Auth0 token
TOKEN=$(python get_token.py)

curl -X POST "http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com/products/multipart" \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Wireless Mouse" \
  -F "description=Ergonomic wireless mouse with USB receiver" \
  -F "category=Electronics" \
  -F "price=29.99" \
  -F "image=@/path/to/mouse.jpg"
```

### Create Product Text-Only (Python)
```python
import requests
import subprocess

# Get authentication token
token = subprocess.check_output(['python', 'get_token.py']).decode().strip()
headers = {"Authorization": f"Bearer {token}"}

product = {
    "name": "Mechanical Keyboard",
    "description": "RGB mechanical keyboard with blue switches",
    "category": "Electronics",
    "price": 79.99
}

response = requests.post(
    "http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com/products/text-only",
    json=product,
    headers=headers
)
print(response.json())
```

### Text Search (Python)
```python
import requests

search_request = {
    "query": "patient bed adjustable",
    "top_k": 5
}

response = requests.post(
    "http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com/search/text",
    json=search_request
)

for result in response.json():
    product = result['product']
    score = result['similarity_score']
    print(f"{product['name']}: {score:.3f}")
```

### Image Search (Python)
```python
import requests

with open('product_image.jpg', 'rb') as f:
    files = {'image': f}
    data = {'top_k': 5}
    response = requests.post(
        "http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com/search/image",
        files=files,
        data=data
    )

for result in response.json():
    print(f"{result['product']['name']}: {result['similarity_score']:.2f}")
```

## AWS ECS Deployment

### Current Production Infrastructure

- **Load Balancer**: `inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com`
- **RDS Endpoint**: `inventory-ai-db.cwjko2wgq241.us-east-1.rds.amazonaws.com`
- **Region**: `us-east-1`
- **Cluster**: `inventory-ai-cluster`
- **Services**: API (2 tasks) + Dashboard (1 task)

### Prerequisites
- AWS CLI configured with appropriate credentials
- PowerShell 7+ (for Windows deployment)
- Docker installed and running
- Auth0 account with configured application
- AWS Account with:
  - VPC with public subnets
  - ECR repositories
  - IAM permissions for ECS, RDS, S3, Secrets Manager

### Automated Deployment

Use the PowerShell deployment script for complete infrastructure setup:

```powershell
# Set up your credentials in environment variables
$env:AWS_ACCESS_KEY_ID = "your-access-key"
$env:AWS_SECRET_ACCESS_KEY = "your-secret-key"
$env:AUTH0_DOMAIN = "your-domain.auth0.com"
$env:AUTH0_CLIENT_ID = "your-client-id"
$env:AUTH0_CLIENT_SECRET = "your-client-secret"
$env:AUTH0_API_AUDIENCE = "your-api-audience"
$env:S3_BUCKET_NAME = "your-s3-bucket"
$env:DB_MASTER_PASSWORD = "YourSecurePassword123!"

# Run deployment
.\deployment\deploy-to-aws.ps1 -Region us-east-1 -AccountId YOUR_ACCOUNT_ID -VpcId YOUR_VPC_ID
```

The script will:
1. Create ECR repositories
2. Build and push Docker images
3. Create RDS PostgreSQL instance with pgvector
4. Set up Application Load Balancer
5. Create ECS cluster and services
6. Configure security groups and IAM roles
7. Store secrets in AWS Secrets Manager
8. Set up CloudWatch logging

### Manual Configuration

1. **Copy and configure deployment settings**:
```bash
cp deployment/config.example.json deployment/config.json
# Edit config.json with your AWS account details and credentials
```

2. **Build Docker images locally** (optional):
```bash
docker-compose build
```

3. **Push images to ECR**:
```powershell
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag inventory-ai-api:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/inventory-ai-api:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/inventory-ai-api:latest
```

## ML Models

The system uses two types of embeddings:

1. **Multimodal Embeddings** (CLIP ViT-B/32)
   - Combines image and text features
   - 512-dimensional vectors
   - Best for products with images

2. **Text-Only Embeddings** (all-MiniLM-L6-v2)
   - Text semantic similarity
   - 384-dimensional vectors
   - Fallback for text-only products

Models are automatically downloaded on first use.

## Database Schema

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    image_url VARCHAR(512),
    s3_key VARCHAR(512),
    category VARCHAR(100),
    price FLOAT,
    multimodal_embedding vector(512),  -- CLIP embeddings
    text_embedding vector(384),        -- Text embeddings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient similarity search
CREATE INDEX ON products USING ivfflat (multimodal_embedding vector_cosine_ops);
CREATE INDEX ON products USING ivfflat (text_embedding vector_cosine_ops);
```

## Configuration

### Environment Variables

All configuration is managed through environment variables. **Never commit secrets to git.**

**Required for Production:**
- `DATABASE_URL`: PostgreSQL connection string with pgvector
- `AWS_ACCESS_KEY_ID`: AWS credentials (use IAM roles in production)
- `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET_NAME`: S3 bucket for images
- `AUTH0_DOMAIN`: Your Auth0 tenant domain
- `AUTH0_API_AUDIENCE`: Auth0 API identifier
- `AUTH0_ALGORITHMS`: JWT algorithm (default: RS256)

**Optional:**
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `DASHBOARD_HOST`: Dashboard host (default: 0.0.0.0)
- `DASHBOARD_PORT`: Dashboard port (default: 8050)
- `EMBEDDING_MODEL`: Multimodal model (default: openai/clip-vit-base-patch32)
- `TEXT_EMBEDDING_MODEL`: Text model (default: sentence-transformers/all-MiniLM-L6-v2)
- `LOG_LEVEL`: Logging level (default: INFO)

### Security Best Practices

1. **Use AWS Secrets Manager** in production (automatic with deployment script)
2. **Never hardcode credentials** - use environment variables
3. **Rotate credentials regularly** - especially after any exposure
4. **Use IAM roles** for ECS tasks instead of access keys when possible
5. **Keep `deployment/config.json` out of git** - it's in `.gitignore`

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Project Structure
- `api/`: FastAPI application
- `dashboard/`: Dash dashboard application  
- `shared/`: Shared code (database, ML, S3)
- `deployment/`: ECS deployment configuration
- `tests/`: Test suite

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running and pgvector extension is installed
- Verify DATABASE_URL in .env file
- Check database credentials and network connectivity

### S3 Upload Failures
- Verify AWS credentials are configured correctly
- Ensure S3 bucket exists and has proper permissions
- Check IAM role has S3 write permissions

### Model Loading Issues
- First run may take time to download ML models
- Ensure sufficient disk space (models are ~500MB total)
- Check internet connectivity for model downloads

### Docker Issues
- Ensure Docker daemon is running
- Check port conflicts (8000, 8050, 5432)
- Verify sufficient system resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/hpanchalCop/inventory.ai/issues
- Documentation: See this README

## Tech Stack

- **Backend**: FastAPI 0.104+, Python 3.10+
- **Frontend**: Plotly Dash, Dash Bootstrap Components
- **Authentication**: Auth0, PyJWT
- **Database**: PostgreSQL 15.8 with pgvector extension
- **ML Models**: 
  - OpenAI CLIP ViT-B/32 (multimodal embeddings)
  - Sentence Transformers all-MiniLM-L6-v2 (text embeddings)
  - PyTorch backend
- **Cloud Infrastructure**:
  - AWS ECS Fargate (container orchestration)
  - AWS RDS (managed PostgreSQL)
  - AWS S3 (object storage)
  - AWS Application Load Balancer
  - AWS CloudWatch (logging & monitoring)
  - AWS Secrets Manager (credential management)
  - AWS ECR (container registry)
- **Containerization**: Docker, Docker Compose
- **DevOps**: PowerShell deployment automation, GitHub