#!/usr/bin/env bash
# Build Command en Render: bash build.sh
#
# Va acá y no en el Procfile porque en Render el "release phase" corre en
# una instancia separada del contenedor final que sirve "web" — lo que
# collectstatic escriba ahí no llega a producción. Solo lo que corre en
# el build queda en la imagen que finalmente se despliega.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
