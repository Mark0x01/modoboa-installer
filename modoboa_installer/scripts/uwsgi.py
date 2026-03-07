"""uWSGI related tools."""

import os
import pwd
import stat

from .. import package
from .. import system
from .. import utils

from . import base


class Uwsgi(base.Installer):
    """uWSGI installer."""

    appname = "uwsgi"
    packages = {
        "deb": ["uwsgi", "uwsgi-plugin-python3"],
        "rpm": ["uwsgi", "uwsgi-plugin-python36"],
        "pkg": ["uwsgi-py311"]
    }

    def get_socket_path(self, app):
        """Return socket path."""
        if package.backend.FORMAT == "deb":
            return "/run/uwsgi/app/{}_instance/socket".format(app)
        if package.backend.FORMAT == "pkg":
            return "/tmp/{}_instance.sock".format(app)
        return "/run/uwsgi/{}_instance.sock".format(app)

    def get_template_context(self, app):
        """Additionnal variables."""
        context = super(Uwsgi, self).get_template_context()
        if package.backend.FORMAT == "deb":
            uwsgi_plugin = "python3"
        if package.backend.FORMAT == "pkg":
            uwsgi_plugin = ""
        else:
            uwsgi_plugin = "python36"

        context.update({
            "app_user": self.config.get(app, "user"),
            "app_venv_path": self.config.get(app, "venv_path"),
            "app_instance_path": (
                self.config.get(app, "instance_path")),
            "uwsgi_socket_path": self.get_socket_path(app),
            "uwsgi_plugin": uwsgi_plugin,
        })

        return context

    def get_config_dir(self):
        """Return appropriate configuration directory."""
        if package.backend.FORMAT == "deb":
            return os.path.join(self.config_dir, "apps-available")
        if package.backend.FORMAT == "pkg":
            """bug in pkg - default paths are missing"""
            utils.exec_cmd("mkdir -p /usr/local/etc/uwsgi/vassals")
            return "{}".format(self.config_dir)

        return "{}.d".format(self.config_dir)

    def _enable_config_debian(self, dst):
        """Enable config file."""
        link = os.path.join(
            self.config_dir, "apps-enabled", os.path.basename(dst))
        if os.path.exists(link):
            return
        os.symlink(dst, link)

    def _setup_config(self, app):
        """Common setup code."""
        context = self.get_template_context(app)
        src = self.get_file_path("{}.ini.tpl".format(app))
        dst = os.path.join(
            self.get_config_dir(), "{}_instance.ini".format(app))
        utils.copy_from_template(src, dst, context)
        return dst

    def _setup_modoboa_config(self):
        """Custom modoboa configuration."""
        dst = self._setup_config("modoboa")
        if package.backend.FORMAT == "deb":
            self._enable_config_debian(dst)
        else:
            system.add_user_to_group(
                "uwsgi", self.config.get("modoboa", "user"))
            utils.exec_cmd("chmod -R g+w {}/media".format(
                self.config.get("modoboa", "instance_path")))
            utils.exec_cmd("chmod -R g+w {}/pdfcredentials".format(
                self.config.get("modoboa", "home_dir")))
            pattern = (
                "s/emperor-tyrant = true/emperor-tyrant = false/")

            #This needs improvement @TODO@
            if package.backend.FORMAT == "pkg":
                #disable plugins=python3
                utils.exec_cmd(
                    "perl -pi -e 's/plugins = /#plugins =/' /usr/local/etc/uwsgi/modoboa_instance.ini")
                # set modoboa_instance.ini as default config file
                dst = os.path.join(self.get_config_dir(), "modoboa_instance.ini")
                utils.exec_cmd("sysrc uwsgi_configfile={}".format(dst))

            else:
                utils.exec_cmd(
                   "perl -pi -e '{}' /etc/uwsgi.ini".format(pattern))

    def post_run(self):
        """Additionnal tasks."""
        self._setup_modoboa_config()

    def restart_daemon(self):
        """Restart daemon process."""
        if package.backend.FORMAT == "pkg":
            system.enable_service("uwsgi")
        # Temp. fix for CentOS
        if utils.dist_name().startswith("centos"):
            pw = pwd.getpwnam("uwsgi")
            utils.mkdir(
                "/run/uwsgi",
                stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH,
                pw[2], pw[3]
            )
        code, output = utils.exec_cmd("service uwsgi status")
        action = "start" if code else "restart"
        utils.exec_cmd("service uwsgi {}".format(action))
