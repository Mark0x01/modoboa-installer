"""Nginx related tools."""

import os

from .. import package
from .. import system
from .. import utils

from . import base
from .uwsgi import Uwsgi


class Nginx(base.Installer):
    """Nginx installer."""

    appname = "nginx"
    packages = {
        "deb": ["nginx", "ssl-cert"],
        "rpm": ["nginx"],
        "pkg": ["nginx", "pcre2", "gsed"]
    }

    def get_template_context(self):
        """Additionnal variables."""
        context = super().get_template_context()
        context.update({
            "app_instance_path": (
                self.config.get("modoboa", "instance_path")),
            "uwsgi_socket_path": (
                Uwsgi(self.config, self.upgrade, self.restore).get_socket_path("modoboa")
            )
        })
        return context

    def _setup_config(self, app, hostname=None, extra_config=None):
        """Custom app configuration."""
        if hostname is None:
            hostname = self.config.get("general", "hostname")
        context = self.get_template_context()
        context.update({"hostname": hostname, "extra_config": extra_config})
        src = self.get_file_path("{}.conf.tpl".format(app))
        group = None
        if package.backend.FORMAT == "deb":
            dst = os.path.join(
                self.config_dir, "sites-available", "{}.conf".format(hostname))
            utils.copy_from_template(src, dst, context)
            link = os.path.join(
                self.config_dir, "sites-enabled", os.path.basename(dst))
            if os.path.exists(link):
                return
            os.symlink(dst, link)
            if self.config.has_section(app):
                group = self.config.get(app, "user")
            user = "www-data"
        elif package.backend.FORMAT == "pkg":
            #conf.d is not standard in FreeBSD
            """no conf.d by default for freebsd 13"""
            utils.exec_cmd("mkdir -p  /usr/local/etc/nginx/conf.d")
            dst = os.path.join(
                self.config_dir, "conf.d", "{}.conf".format(hostname))
            utils.copy_from_template(src, dst, context)
            group = "uwsgi"
            user = "www"
        else:
            dst = os.path.join(
                self.config_dir, "conf.d", "{}.conf".format(hostname))
            utils.copy_from_template(src, dst, context)
            group = "uwsgi"
            user = "nginx"
        if user and group:
            system.add_user_to_group(user, group)

    def post_run(self):
        """Additionnal tasks."""
        extra_modoboa_config = ""

        hostname = "autoconfig.{}".format(
            self.config.get("general", "domain"))
        self._setup_config("autoconfig", hostname)

        if self.config.get("radicale", "enabled"):
            extra_modoboa_config += """
    location /radicale/ {
        proxy_pass http://localhost:5232/; # The / is important!
        proxy_set_header X-Script-Name /radicale;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass_header Authorization;
    }
"""
        self._setup_config(
            "modoboa", extra_config=extra_modoboa_config)
        if package.backend.FORMAT == "pkg":
             # need to use gsed at this time.
             # this appears to be run twice, so check first
             # fix with sed -n '/pattern/!p;$a pattern'

            path = "/usr/local/etc/nginx/nginx.conf"
            code, output = utils.exec_cmd(
                r"grep 'include /usr/local/etc/nginx/conf.d' {}".format(path))
            if code:
                utils.exec_cmd(
                    "gsed -i.bak '122i\include /usr/local/etc/nginx/conf.d/*.conf;' /usr/local/etc/nginx/nginx.conf" 
                    )
        if not os.path.exists("{}/dhparam.pem".format(self.config_dir)):
            cmd = "openssl dhparam -dsaparam -out dhparam.pem 4096"
            utils.exec_cmd(cmd, cwd=self.config_dir)
