[program:modoboa-privileged-worker]
autostart=true
autorestart=true
command=%{venv_path}/bin/python %{home_dir}/instance/manage.py rqworker privileged
directory=%{home_dir}
user=root
redirect_stderr=true
numprocs=1
stopsignal=TERM
