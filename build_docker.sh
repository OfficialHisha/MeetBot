docker stop meetbot
docker rm meetbot
docker rmi meetbot
docker build -t meetbot .
docker run --restart unless-stopped --name meetbot -d meetbot
