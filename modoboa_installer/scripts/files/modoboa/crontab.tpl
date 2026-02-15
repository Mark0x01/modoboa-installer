#
# Modoboa specific cron jobs
#
PYTHON=%{venv_path}/bin/python
INSTANCE=%{instance_path}
MAILTO=%{cron_error_recipient}

# Sessions table cleanup
0       0       *       *       *       root    $PYTHON $INSTANCE/manage.py clearsessions
