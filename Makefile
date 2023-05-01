update-models:
	sqlacodegen mysql+mysqlconnector://root@127.0.0.1:3309/schulz --outfile app/models.py

build-image:
	docker build -t schulz-backend .

run-container:
	docker run -d -p 80:80 --name schulz-backend --env-file .env schulz-backend 

restart:
	docker build -t schulz-backend . && docker stop schulz-backend && docker container prune -f && docker run -d -p 80:80 --env-file .env --name schulz-backend schulz-backend
