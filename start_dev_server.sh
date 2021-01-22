#!/bin/sh

# NOTE: the file env must end with a newline
# todo: add a newline to the end of env file automatically if it does not

# populate env var
while IFS= read -r line; do
    if [ -n "$line" -a "${line:0:1}" != "#" ]; then
        export "$line"
	fi
done < config/env

(
bash -c "conda activate py38-sccm" 2>/dev/null
python manage.py runserver -h 0.0.0.0 -p 5000 --threaded
#python run.py
)
