release: python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && python manage.py setup_railway
web: daphne pmbeta.asgi:application --port $PORT --bind 0.0.0.0 --verbosity 2
