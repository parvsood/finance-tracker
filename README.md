
# Personal Finance Tracker

Track your finances and set goals to help you grow and prosper.



## Deployment

To deploy this project run the following commands sequentially.

```bash
  python -m venv my-env
```

```bash
  my-env\bin\activate
```

```bash
  pip install -r requirements
```
then cd to the project folder and hit the following commands: 
```bash
python manage.py makemigrations
python manage.py migrate
```
then cd to the flask_api folder and hit the following command: 
```bash
python app.py
```

Similarly open a new terminal activate the virtual environment, cd to the project folder and hit the following commands:

To run the django project

```bash
python manage.py runserver
```




