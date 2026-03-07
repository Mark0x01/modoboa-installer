"""Spamassassin related functions."""

import os
import pwd
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
    
from .. import package
from .. import utils
from .. import system

from . import base
from . import install


class Spamassassin(base.Installer):

    """SpamAssassin installer."""

    appname = "spamassassin"
    no_daemon = True
    packages = {
        "deb": ["spamassassin", "pyzor"],
        "rpm": ["spamassassin", "pyzor"],
        "pkg": ["spamassassin"]
    }
    with_db = True
    config_files = ["v310.pre", "local.cf"]

    def get_sql_schema_path(self):
        """Return SQL schema."""
        if self.dbengine == "postgres":
            fname = "bayes_pg.sql"
        else:
            fname = "bayes_mysql.sql"
        schema = "/usr/share/doc/spamassassin/sql/{}".format(fname)
        if package.backend.FORMAT == "pkg":
            schema = "/usr/local/share/doc/spamassassin/sql/{}".format(fname)
        if not os.path.exists(schema):
            version = package.backend.get_installed_version("spamassassin")
            version = version.replace(".", "_")
            url = (
                "http://svn.apache.org/repos/asf/spamassassin/tags/"
                "spamassassin_release_{}/sql/{}".format(version, fname))
            schema = "/tmp/{}".format(fname)
            utils.exec_cmd("wget {} -O {}".format(url, schema))
        return schema

    def get_template_context(self):
        """Add additional variables to context."""
        context = super(Spamassassin, self).get_template_context()
        if self.dbengine == "postgres":
            store_module = "Mail::SpamAssassin::BayesStore::PgSQL"
            dsn = "DBI:Pg:dbname={};host={};port={}".format(
                self.dbname, self.dbhost, self.dbport)
        else:
            store_module = "Mail::SpamAssassin::BayesStore::MySQL"
            dsn = "DBI:mysql:{}:{}:{}".format(
                self.dbname, self.dbhost, self.dbport)
        context.update({
            "store_module": store_module, "dsn": dsn, "dcc_enabled": "#"})
# now done in run.py
#        if package.backend.FORMAT == "pkg":
#            context.update({"config_dir": "/usr/local/etc/mail/spamassassin", "pyzor_bin_path": "/usr/local/bin/pyzor"})

        return context

    def post_run(self):
        """Additional tasks."""
        install("razor", self.config, self.upgrade, self.restore)
        if utils.dist_name() in ["debian", "ubuntu"]:
            utils.exec_cmd(
                "perl -pi -e 's/^CRON=0/CRON=1/' /etc/cron.daily/spamassassin")

        if 'freebsd' in utils.dist_name():
            #daemon sa-spamd, rc name spamd. 
              utils.exec_cmd("sa-update")
              system.enable_service("spamd")
              system.restart_service("sa-spamd")
