update-models:
	sqlacodegen mysql+mysqlconnector://root@127.0.0.1:3309/schulz --outfile app/models.py