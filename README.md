# inventory.ai

AI-powered inventory management system with multimodal embeddings for intelligent product matching and search.

## Features

### FastAPI Microservice
- **Multipart Requests**: Support for image + text product uploads
- **Text-Only Support**: Create products with descriptions only
- **Multimodal Embeddings**: Combined image + text embeddings using CLIP for enhanced product matching
- **Text-Only Semantic Similarity**: Fallback to text-only embeddings for products without images
- **RESTful API**: Complete CRUD operations for product management
- **Similarity Search**: Find similar products based on embeddings

### Storage System
- **AWS S3**: Scalable storage for product images and ML metadata
- **PostgreSQL + pgvector**: Store product metadata and vector embeddings for efficient similarity search

### Plotly Dash Admin Dashboard
- **Product Management**: Add, view, and manage products through an intuitive web interface
- **Analytics**: Visualize product distribution by category and price
- **Real-time Stats**: Monitor total products, categories, and other key metrics
- **Auto-refresh**: Dashboard updates automatically every 30 seconds

### Containerized Deployment
- **Docker Images**: Separate containers for FastAPI service and Dash dashboard
- **Local Development**: Easy setup with docker-compose
- **AWS ECS**: Production-ready deployment configuration for AWS Elastic Container Service

## Architecture

```
inventory.ai/
├── api/                    # FastAPI microservice
│   └── main.py            # API endpoints and business logic
├── dashboard/             # Plotly Dash admin interface
│   └── app.py            # Dashboard application
├── shared/                # Shared modules
│   ├── config.py         # Configuration management
│   ├── database.py       # Database models and setup
│   ├── ml_service.py     # ML embeddings service
│   └── s3_service.py     # AWS S3 integration
├── deployment/            # Deployment configurations
│   ├── ecs-task-definition-api.json
│   ├── ecs-task-definition-dashboard.json
│   └── deploy-ecs.sh
├── Dockerfile.api         # API container definition
├── Dockerfile.dashboard   # Dashboard container definition
├── docker-compose.yml     # Local development setup
└── requirements.txt       # Python dependencies
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

- `POST /products/multipart` - Create product with image and text
  - Form fields: `name`, `description`, `category`, `price`, `image` (file)
  
- `POST /products/text-only` - Create product with text only
  - JSON body: `{"name": "...", "description": "...", "category": "...", "price": 0.0}`

- `GET /products` - List all products
  - Query params: `skip`, `limit`, `category`

- `GET /products/{product_id}` - Get specific product

- `DELETE /products/{product_id}` - Delete product

### Search

- `POST /search/similar` - Find similar products
  - JSON body: `{"product_id": 1, "top_k": 5, "use_multimodal": true}`

### Health

- `GET /health` - Health check endpoint

## API Usage Examples

### Create Product with Image (cURL)
```bash
curl -X POST "http://localhost:8000/products/multipart" \
  -F "name=Wireless Mouse" \
  -F "description=Ergonomic wireless mouse with USB receiver" \
  -F "category=Electronics" \
  -F "price=29.99" \
  -F "image=@/path/to/mouse.jpg"
```

### Create Product Text-Only (Python)
```python
import requests

product = {
    "name": "Mechanical Keyboard",
    "description": "RGB mechanical keyboard with blue switches",
    "category": "Electronics",
    "price": 79.99
}

response = requests.post(
    "http://localhost:8000/products/text-only",
    json=product
)
print(response.json())
```

### Search Similar Products (Python)
```python
import requests

search_request = {
    "product_id": 1,
    "top_k": 5,
    "use_multimodal": True
}

response = requests.post(
    "http://localhost:8000/search/similar",
    json=search_request
)

for result in response.json():
    print(f"{result['product']['name']}: {result['similarity_score']:.2f}")
```

## AWS ECS Deployment

### Prerequisites
- AWS CLI configured
- ECR repositories created
- ECS cluster set up
- RDS PostgreSQL instance with pgvector
- S3 bucket created

### Deploy to ECS

1. **Configure deployment**:
Edit `deployment/ecs-task-definition-api.json` and `deployment/ecs-task-definition-dashboard.json` with your:
- AWS Account ID
- ECR registry URL
- RDS endpoint
- IAM role ARNs

2. **Set environment variables**:
```bash
export ECR_REGISTRY=YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
export CLUSTER_NAME=inventory-ai-cluster
export API_SERVICE_NAME=inventory-ai-api-service
export DASHBOARD_SERVICE_NAME=inventory-ai-dashboard-service
```

3. **Run deployment script**:
```bash
./deployment/deploy-ecs.sh
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

All configuration is managed through environment variables. See `.env.example` for available options:

- `DATABASE_URL`: PostgreSQL connection string
- `AWS_ACCESS_KEY_ID`: AWS credentials
- `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET_NAME`: S3 bucket for images
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `DASHBOARD_HOST`: Dashboard host (default: 0.0.0.0)
- `DASHBOARD_PORT`: Dashboard port (default: 8050)
- `EMBEDDING_MODEL`: Multimodal model name
- `TEXT_EMBEDDING_MODEL`: Text-only model name

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

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: Plotly Dash, Bootstrap
- **Database**: PostgreSQL with pgvector
- **ML**: Sentence Transformers, CLIP, PyTorch
- **Cloud**: AWS S3, AWS ECS
- **Containerization**: Docker, Docker Compose