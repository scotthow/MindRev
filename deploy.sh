
# Set environment variables
export PROJECT_ID=""
export PROJECT_NUM=""
export REGION="us-central1"
export SERVICE_NAME=""
export SERVICE_ACCOUNT=""

# Set project
gcloud config set project $PROJECT_ID

# Enable the Cloud Run Admin API and the Cloud Build API. 
# After the Cloud Run Admin API is enabled, the Compute Engine 
# default service account is automatically created.
gcloud services enable run.googleapis.com \
cloudbuild.googleapis.com

# For Cloud Build to be able to build your sources, grant the 
# Cloud Build Service Account role to the Compute Engine default service 
# account by running the following:
gcloud projects add-iam-policy-binding $PROJECT_ID \
--member=serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com \
--role=roles/cloudbuild.builds.builder

# Wait and verify permissions
echo "Waiting for permissions to propagate..."
sleep 20

echo "Current project: $(gcloud config get-value project)"
echo "Current account: $(gcloud config get-value account)"

# Deploy from source automatically builds a container image from source code 
# and deploys it. In your source code directory, deploy the current folder 
# using the following command:
gcloud run deploy --source .

# Get the API URL
URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')

# Print deployment information
echo URL: ${URL}

