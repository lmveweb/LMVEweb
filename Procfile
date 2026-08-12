release: python manage.py migrate && python manage.py createcachetable
web: gunicorn LMVEweb.wsgi:application --bind 0.0.0.0:$PORT
