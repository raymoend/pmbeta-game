release: python manage.py migrate && python manage.py collectstatic --noinput
web: daphne pmbeta.asgi:application --port $PORT --bind 0.0.0.0
