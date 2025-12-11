# Local Setup Guide for inventory.ai

This guide walks you through setting up PostgreSQL with pgvector and AWS S3 for local development.

---

## Part 1: PostgreSQL Setup

### Step 1: Install PostgreSQL

**Windows:**
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer and follow the setup wizard
3. During installation:
   - Choose a password for the `postgres` user (remember this!)
   - Default port is `5432`
   - Default username is `postgres`
4. Complete the installation

**Verify Installation:**
```bash
psql --version
```

### Step 2: Create the Database

1. **Open PostgreSQL Command Line** (psql):
   - Windows: Search for "SQL Shell (psql)" or run:
   ```bash
   psql -U postgres
   ```
   - Enter the password you set during installation

2. **Create the database**:
   ```sql
   CREATE DATABASE inventory_db;
   ```

3. **Verify creation**:
   ```sql
   \l
   ```
   (You should see `inventory_db` in the list)

### Step 3: Install pgvector Extension

1. **Connect to the new database**:
   ```sql
   \c inventory_db
   ```

2. **Create the pgvector extension**:
   ```sql
   CREATE EXTENSION vector;
   ```

3. **Verify installation**:
   ```sql
   \dx
   ```
   (You should see `vector` in the extensions list)

4. **Exit psql**:
   ```sql
   \q
   ```

### Step 4: Update .env File

Create or edit `.env` file in the project root with your PostgreSQL connection:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/inventory_db
```

Replace `your_password` with the password you set during PostgreSQL installation.

### Running PostgreSQL for development (options)

If you're preparing a local development environment you can run PostgreSQL in several ways. The recommended approach for Windows developers is to use Docker (pgvector is already available in many images). If you prefer native Windows or WSL, follow the notes below.

- Option A — Docker (recommended on Windows):
  1. Start a Postgres image that includes pgvector (example uses `ankane/pgvector`):
     ```powershell
     docker run -d --name inventory-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 ankane/pgvector:latest
     ```
  2. Create the database and extension inside the container:
     ```powershell
     docker exec -it inventory-db psql -U postgres -c "CREATE DATABASE inventory_db;"
     docker exec -it inventory-db psql -U postgres -d inventory_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
     docker exec -it inventory-db psql -U postgres -d inventory_db -c "\dx"
     ```
  3. Update your `.env` to point to the container (default password `postgres` in the example):
     ```bash
     DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inventory_db
     ```

- Option B — Native Windows Postgres (service):
  - If you installed PostgreSQL using the Windows installer, the server runs as a Windows service. You can start/stop it from Services.msc or PowerShell:
    ```powershell
    # Check service name (common names include 'postgresql-x64-18' or similar)
    Get-Service | Where-Object {$_.Name -like '*postgres*'}
    # Stop service
    Stop-Service -Name 'postgresql-x64-18'
    # Start service
    Start-Service -Name 'postgresql-x64-18'
    ```
  - Important: Installing `pgvector` on native Windows is non-trivial because it is a C extension that usually requires building with a Visual C++ toolchain and matching `pg_config`. If you need pgvector and prefer not to build locally, use Option A (Docker) or Option C (WSL).

- Option C — WSL / Linux (recommended if you want native build):
  1. In WSL (Ubuntu) install build dependencies and postgresql dev packages:
     ```bash
     sudo apt update
     sudo apt install -y build-essential postgresql postgresql-server-dev-all git
     ```
  2. Build and install pgvector:
     ```bash
     git clone https://github.com/pgvector/pgvector.git
     cd pgvector
     make
     sudo make install
     ```
  3. Restart PostgreSQL and enable the extension in your database:
     ```bash
     sudo service postgresql restart
     sudo -u postgres psql -d inventory_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
     ```

Notes:
- If you already have a native Postgres running on port 5432 you must stop it before binding the Docker container to that port or use another host port (e.g., `-p 5433:5432`).
- The Docker option is the quickest path on Windows to get a Postgres server with `pgvector` available.

---

## Part 2: AWS S3 Setup

### Step 1: Create AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the registration process
4. Verify your email and complete account setup

### Step 2: Create an S3 Bucket

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Navigate to S3**:
   - Search for "S3" in the services search bar
   - Click on "S3"
3. **Create a new bucket**:
   - Click "Create bucket" button
   - **Bucket name**: `inventory-ai-bucket` (must be globally unique, so consider adding a timestamp or your name)
   - **Region**: Choose the closest region to you (e.g., `us-east-1`)
   - **Block Public Access settings**: Keep defaults (checked)
   - Click "Create bucket"

### Step 3: Generate AWS Access Keys

Important security note: Do NOT generate or use access keys for the AWS account root user except in emergencies. Create an IAM user with programmatic access and the minimum required permissions for S3 access, then generate access keys for that IAM user.

Console (recommended for most users):
1. Sign in to the AWS Management Console using your root account or an administrator IAM user.
2. Open the IAM console: https://console.aws.amazon.com/iam/
3. Create a new IAM user for the application:
   - Click "Users" → "Add users"
   - Enter a username (e.g., `inventory-app-user`)
   - Select **Programmatic access** (gives an Access Key ID and Secret)
   - Click "Next: Permissions"

4. Attach permissions now or attach a custom policy later (see Step 4). Finish creating the user.

5. When prompted, download or copy the **Access Key ID** and **Secret Access Key**. Save these securely — the secret is shown only once.

AWS CLI (alternative):
1. Create the IAM user (run as an admin; this does not create keys yet):
```powershell
aws iam create-user --user-name inventory-app-user
```
2. Create programmatic credentials for the user and capture the output JSON:
```powershell
aws iam create-access-key --user-name inventory-app-user
```
Save the `AccessKeyId` and `SecretAccessKey` from the command output to a secure place.

Security recommendations:
- Do not use root account access keys for daily operations. If root keys exist, delete them after creating an admin IAM user.
- Enable MFA on the root account and on admin IAM accounts.
- Store keys securely (password manager, OS keyring, or secrets manager). Do not commit to source control.
- Rotate keys regularly.

### Step 4: Grant S3 Permissions (Important!)

Grant permissions to the IAM user you created in Step 3. Prefer least-privilege policies that scope access to your specific bucket rather than `AmazonS3FullAccess`.

Console (attach an existing policy):
1. In the IAM console, go to **Users** and click the username (e.g., `inventory-app-user`).
2. Click **Add permissions** → **Attach policies directly**.
3. For quick testing you can attach `AmazonS3FullAccess`, but for production use create a custom policy scoped to your bucket (example below).

Example minimal S3 policy (restricts to a single bucket):
```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
         "Effect": "Allow",
         "Action": [
            "s3:ListBucket"
         ],
         "Resource": [
            "arn:aws:s3:::inventory-ai-bucket"
         ]
      },
      {
         "Effect": "Allow",
         "Action": [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject"
         ],
         "Resource": [
            "arn:aws:s3:::inventory-ai-bucket/*"
         ]
      }
   ]
}
```

Create and attach this policy via the console (IAM → Policies → Create policy) or with the AWS CLI:

1. Save the JSON above to a file, e.g., `inventory-s3-policy.json`.
2. Create the policy:
```powershell
aws iam create-policy --policy-name InventoryS3LimitedAccess --policy-document file://inventory-s3-policy.json
```
3. Attach the policy to the user:
```powershell
aws iam attach-user-policy --user-name inventory-app-user --policy-arn arn:aws:iam::<YOUR_ACCOUNT_ID>:policy/InventoryS3LimitedAccess
```

Alternatively, for quick testing attach the managed policy:
```powershell
aws iam attach-user-policy --user-name inventory-app-user --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

Notes:
- Replace `<YOUR_ACCOUNT_ID>` with your AWS account ID when using the CLI-created policy ARN.
- After attaching permissions, confirm access by running a simple S3 command with the new credentials (e.g., `aws s3 ls s3://inventory-ai-bucket`).
- If you run locally, configure the AWS CLI profile or set the environment variables in `.env` (see Step 5).

Best practices recap:
- Never store root access keys in your app or repo.
- Use an IAM user (or role) with the narrowest permissions required.
- Enable MFA and rotate credentials regularly.

### Step 5: Update .env File

Add your AWS credentials to the `.env` file:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=inventory-ai-bucket
```

Replace with your actual values from Step 3.

---

## Part 3: Initialize the Application

### Step 1: Install Python Dependencies

Create and activate a Python virtual environment (PowerShell):

```powershell
# Create venv
python -m venv .venv

# Activate venv (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

On bash / WSL / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Initialize the Database

```bash
python init_db.py
```

If you are using a non-superuser `DATABASE_URL` (recommended), ensure the `vector` extension has already been created by a superuser (see Part 1). If `init_db.py` needs additional privileges, run it while `DATABASE_URL` points to a superuser connection or run only the schema-creation portion as `postgres`.

This creates all the necessary tables in `inventory_db`.

### Step 3: (Optional) Load Sample Data

```bash
python populate_sample_data.py
```

This populates the database with sample products for testing.

---

## Part 4: Start the Application

### Option A: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

Access:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8050

### Option B: Manual Start (without Docker)

**Terminal 1 - Start the API**:
```bash
python -m api.main
```
Access at: http://localhost:8000

**Terminal 2 - Start the Dashboard**:
```bash
python -m dashboard.app
```
Access at: http://localhost:8050

---

## Troubleshooting

### PostgreSQL Connection Error
- **Error**: `FATAL: Ident authentication failed for user "postgres"`
  - **Solution**: Check your password in `.env` matches what you set during installation
  - **Solution**: Edit `pg_hba.conf` to change auth method from `ident` to `md5`

### pgvector Extension Not Found
- **Error**: `ERROR: could not open extension control file`
  - **Solution**: Install pgvector: `CREATE EXTENSION vector;` in `inventory_db`
  - **Solution**: If extension not available, install from source or use Docker

### AWS Credentials Error
- **Error**: `InvalidAccessKeyId` or `SignatureDoesNotMatch`
  - **Solution**: Verify Access Key ID and Secret in `.env`
  - **Solution**: Ensure keys haven't been revoked in AWS IAM
  - **Solution**: Wait a few minutes after creating keys (they take time to activate)

### S3 Bucket Access Denied
- **Error**: `AccessDenied: User is not authorized to perform: s3:*`
  - **Solution**: Ensure your IAM user has `AmazonS3FullAccess` policy attached
  - **Solution**: Check bucket name in `.env` matches the one you created

### Port Already in Use
- **Error**: `Address already in use`
  - **Solution**: Change ports in `.env` or kill the process using those ports
  - **Solution**: `netstat -ano | findstr :8000` (PowerShell) to find the process

---

## Security Best Practices

⚠️ **Important**: Never commit `.env` to git!

1. `.env` is already in `.gitignore` (check this)
2. Never share AWS credentials
3. Use AWS IAM roles for production (not access keys)
4. Rotate credentials regularly
5. Consider using AWS Secrets Manager for production

---

## Next Steps

After setup is complete:
1. Access the dashboard at http://localhost:8050
2. Use the API documentation at http://localhost:8000/docs
3. Try adding products with the dashboard or API
4. Verify images are stored in S3 bucket

For questions or issues, check the main `README.md` file.
