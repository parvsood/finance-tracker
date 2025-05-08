
# Personal Finance Tracker

Track your finances and set goals to help you grow and prosper.



## Deployment

To deploy this project run the following commands sequentially.

```bash
  python -m venv my-env
```

```bash
  .\my-env\Scripts\activate   #.\my-env\bin\activate for some systems.
```

```bash
  pip install -r requirements
```

Change the directory to the project folder and hit the following commands: 
```bash
python manage.py makemigrations
python manage.py migrate
```
Move into the flask_api folder and hit the following command: 
```bash
python app.py
```

Now Open a new terminal and activate the virtual environment, Move into the project folder and hit the following commands to run the django project

```bash
python manage.py runserver
```




