docker stop meetbot
docker rm meetbot
docker run --restart unless-stopped --env-file environment --name meetbot -d meetbot
