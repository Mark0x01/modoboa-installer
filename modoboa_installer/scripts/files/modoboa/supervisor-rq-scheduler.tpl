[program:rq-scheduler]
autostart=true
autorestart=true
command=%{venv_path}/bin/python %{home_dir}/instance/manage.py rqcron %{home_dir}/instance/instance/cron_config.py
directory=%{home_dir}
user=%{user}
redirect_stderr=true
numprocs=1
stopsignal=TERM
