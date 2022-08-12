PORT=8880
NAME=ccheckserver
IMAGE=ccheckserver:latest

#docker build --tag $IMAGE -f ./Dockerfile .
docker run --rm -p ${PORT}:80 --name $NAME -v $(pwd)/opt:/root/opt -w /root/opt/ -it $IMAGE python ./scripts/server.py