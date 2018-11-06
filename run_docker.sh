docker stop meetbot
docker rm meetbot
docker run --restart unless-stopped --name meetbot -d meetbot
