## How to Run the Multi-Region Deployment Commands

### **📋 Setup Commands (First Time Only)**

```bash
# 1. Create all template files
chmod +x create-templates.sh
./create-templates.sh

# 2. Make setup script executable
chmod +x setup-environment.sh

# 3. Update AWS Account ID and Callback Code in setup-environment.sh
# Edit the script and replace:
# - "123456789012" with your actual AWS Account ID
# - "your_actual_callback_code_here" with your Pudu callback code
```

### **🚀 Deployment Commands**

#### **Deploy to US-East-1:**
```bash
# Option 1: One command (setup + deploy)
make deploy-us-east-1

# Option 2: Step by step
make setup-us-east-1    # Generate config files
make verify-config      # Check what was generated
make deploy-container   # Deploy to ECR
```

#### **Deploy to US-East-2:**
```bash
# Option 1: One command (setup + deploy)
make deploy-us-east-2

# Option 2: Step by step
make setup-us-east-2    # Generate config files
make verify-config      # Check what was generated
make deploy-container   # Deploy to ECR
```

#### **Just Switch Configuration (without deploying):**
```bash
# Switch to us-east-1 config
make setup-us-east-1

# Switch to us-east-2 config
make setup-us-east-2
```

### **🔍 Verification Commands**

```bash
# Check current configuration
make verify-config

# Show all environment variables
make print-vars

# See available commands
make help
```

### **🧹 Utility Commands**

```bash
# Clean generated files (start fresh)
make clean-config

# Manual setup (alternative to make commands)
./setup-environment.sh us-east-1
./setup-environment.sh us-east-2
```

### **📖 Complete Workflow Example**

```bash
# Initial setup (run once)
./create-templates.sh
chmod +x setup-environment.sh

# Edit setup-environment.sh to set your AWS_ACCOUNT_ID and PUDU_CALLBACK_CODE

# Deploy to staging (us-east-2)
make deploy-us-east-2

# Later, deploy to production (us-east-1)
make deploy-us-east-1

# Verify current config anytime
make verify-config

# Clean up when needed
make clean-config
```

### **🎯 Most Common Commands**

**For daily use, you'll mainly use these:**

```bash
# Deploy to us-east-1 (production)
make deploy-us-east-1

# Deploy to us-east-2 (staging)
make deploy-us-east-2

# Check what's currently configured
make verify-config
```

### **⚠️ Important Notes**

1. **First time setup**: Must run `./create-templates.sh` once before anything else
2. **Update script**: Edit `setup-environment.sh` to set your AWS Account ID and Pudu callback code
3. **Region switching**: Each `make setup-*` command overwrites the previous config
4. **File generation**: The setup commands create 4 files each time:
   - `.env` (root)
   - `pudu-webhook-api/.env`
   - `pudu-webhook-api/notifications/.env`
   - `pudu-webhook-api/rds/credentials.yaml`

The beauty of this system is that **`make deploy-us-east-1`** handles everything automatically - it generates the right config files and deploys in one command!