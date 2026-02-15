[program:modoboa-dovecot-worker]
autostart=true
autorestart=true
command=%{venv_path}/bin/python %{home_dir}/instance/manage.py rqworker dovecot
directory=%{home_dir}
user=%{dovecot_mailboxes_owner}
redirect_stderr=true
numprocs=1
stopsignal=TERM
