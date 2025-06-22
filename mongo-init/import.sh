#!/bin/bash
HOST="localhost"
DB="news"
AUTH_DB="admin"
USERNAME="admin"
PASSWORD="password123"

# Common mongoimport parameters
COMMON_PARAMS="--host $HOST --db $DB --authenticationDatabase $AUTH_DB -u $USERNAME -p $PASSWORD"

echo "Starting MongoDB data import..."

# Import articles
echo "Importing articles..."
mongoimport $COMMON_PARAMS --collection articles --type json --file /docker-entrypoint-initdb.d/articles.json --jsonArray

# Import metrics
echo "Importing metrics..."
mongoimport $COMMON_PARAMS --collection metrics --type json --file /docker-entrypoint-initdb.d/metrics.json --jsonArray

# Import predictors
echo "Importing predictors..."
mongoimport $COMMON_PARAMS --collection predictors --type json --file /docker-entrypoint-initdb.d/predictors.json --jsonArray

# Import deployments
echo "Importing deployments..."
mongoimport $COMMON_PARAMS --collection deployments --type json --file /docker-entrypoint-initdb.d/deployments.json --jsonArray

# Import article predictions
echo "Importing article predictions..."
mongoimport $COMMON_PARAMS --collection article_predictions --type json --file /docker-entrypoint-initdb.d/article_predictions.json --jsonArray

echo "MongoDB data import completed successfully!"
