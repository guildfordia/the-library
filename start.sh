#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting The Library...${NC}"

# Start docker compose
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Get the IP addresses
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    IP=$(hostname -I | awk '{print $1}')
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac OSX
    IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
else
    # Default to localhost
    IP="localhost"
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}The Library is running!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Access the application at:"
echo -e "  - From this device: ${BLUE}http://localhost${NC}"
echo -e "  - From other devices on the network: ${BLUE}http://${IP}${NC}"
echo ""
echo -e "To stop the application, run: ${BLUE}docker-compose down${NC}"
echo -e "To view logs, run: ${BLUE}docker-compose logs -f${NC}"
echo ""