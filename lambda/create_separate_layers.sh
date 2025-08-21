#!/bin/bash

# Create working OpenCV layer with proper dependencies and platform targeting

set -e

REGION="us-east-2"
PYTHON_VERSION="3.9"

echo "Creating working OpenCV layer with platform-specific installation"

# Function to create a layer
create_layer() {
    local layer_name="$1"
    local packages="$2"
    local description="$3"

    echo "Creating layer: $layer_name"

    # Create layer directory
    rm -rf /tmp/lambda_layer_${layer_name}
    mkdir -p /tmp/lambda_layer_${layer_name}/python
    cd /tmp/lambda_layer_${layer_name}

    # Install packages with proper platform targeting
    echo "Installing: $packages"
    eval "$packages"

    # Aggressive cleanup
    echo "Cleaning up $layer_name..."
    find python/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find python/ -name "*.pyc" -delete 2>/dev/null || true
    find python/ -name "*.pyo" -delete 2>/dev/null || true
    find python/ -path "*/tests" -type d -exec rm -rf {} + 2>/dev/null || true
    find python/ -name "*.md" -delete 2>/dev/null || true
    find python/ -name "LICENSE*" -delete 2>/dev/null || true
    find python/ -name "*.txt" -delete 2>/dev/null || true
    find python/ -name "*.rst" -delete 2>/dev/null || true
    find python/ -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
    find python/ -name "*.debug" -delete 2>/dev/null || true

    # OpenCV-specific cleanup
    if [[ "$layer_name" == *"opencv"* ]]; then
        rm -rf python/cv2/data 2>/dev/null || true
        rm -rf python/opencv_python_headless.libs 2>/dev/null || true
        # Remove duplicate .so files but keep the main ones
        find python/ -name "*.so.*" -delete 2>/dev/null || true
    fi

    # Strip shared libraries to reduce size
    if command -v strip >/dev/null 2>&1; then
        find python/ -name "*.so" -exec strip {} + 2>/dev/null || true
    fi

    echo "Creating ZIP for $layer_name..."
    zip -r ${layer_name}.zip python/ -q

    # Check size
    local zip_size=$(stat -f%z ${layer_name}.zip 2>/dev/null || stat -c%s ${layer_name}.zip)
    local zip_size_mb=$((zip_size / 1024 / 1024))
    echo "$layer_name ZIP size: ${zip_size_mb}MB"

    if [ $zip_size -gt 52428800 ]; then  # 50MB
        echo "$layer_name still too large (${zip_size_mb}MB)"
        return 1
    fi

    echo "Publishing $layer_name..."
    local layer_arn=$(aws lambda publish-layer-version \
        --layer-name $layer_name \
        --description "$description" \
        --zip-file fileb://${layer_name}.zip \
        --compatible-runtimes python${PYTHON_VERSION} \
        --region $REGION \
        --query 'LayerVersionArn' \
        --output text)

    echo "$layer_name created: $layer_arn"
    echo "$layer_arn" >> /tmp/layer_arns.txt

    cd /
    rm -rf /tmp/lambda_layer_${layer_name}
}

# Clear the ARNs file
rm -f /tmp/layer_arns.txt

# Create OpenCV layer WITH its dependencies (including numpy)
# Use platform-specific installation to ensure Lambda compatibility
# Create OpenCV layer without deps, then add numpy
create_layer "pudu-opencv-complete" \
    "pip install --platform manylinux2014_x86_64 --target python/ --implementation cp --python-version ${PYTHON_VERSION} --only-binary=:all: --no-deps opencv-python-headless==4.5.5.64 --quiet && pip install --platform manylinux2014_x86_64 --target python/ --implementation cp --python-version ${PYTHON_VERSION} --only-binary=:all: numpy --quiet" \
    "OpenCV headless with numpy for Lambda"

create_layer "pudu-pillow-platform" \
    "pip install --platform manylinux2014_x86_64 --target python/ --implementation cp --python-version ${PYTHON_VERSION} --only-binary=:all: --upgrade Pillow==9.5.0 --quiet" \
    "Pillow (PIL) for image processing - Lambda compatible"

echo ""
echo "Both layers created successfully!"
echo ""
echo "Layer ARNs:"
cat /tmp/layer_arns.txt
echo ""
echo "Update your deployment script to use these layers:"
PILLOW_ARN=$(sed -n '2p' /tmp/layer_arns.txt)
OPENCV_ARN=$(sed -n '1p' /tmp/layer_arns.txt)
echo "PILLOW_LAYER_ARN=\"$PILLOW_ARN\""
echo "OPENCV_LAYER_ARN=\"$OPENCV_ARN\""