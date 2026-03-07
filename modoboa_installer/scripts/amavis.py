"""Amavis related functions."""

import os

from .. import package
from .. import utils
from .. import system
from . import base
from . import backup, install


class Amavis(base.Installer):

    """Amavis installer."""

    appname = "amavis"
    packages = {
        "deb": [
            "libdbi-perl", "amavisd-new", "arc", "arj", "cabextract",
            "liblz4-tool", "lrzip", "lzop", "p7zip-full", "rpm2cpio",
            "unrar-free"
        ],
        "rpm": [
            "amavisd-new", "arj", "lz4", "lzop", "p7zip"
        ],
         "pkg": [ "amavisd-new", "arj", "liblz4", "lzop", "7-zip","arc","rpm2cpio"
        ],
    }
    with_db = True

    @property
    def config_dir(self):
        """Return appropriate config dir."""
        if utils.ENV.get("debug"):
            utils.printcolor(
                "amavis.py: config_dir",utils.YELLOW)
        if package.backend.FORMAT == "rpm":
            return "/etc/amavisd"
        if package.backend.FORMAT == "pkg":
            return "/usr/local/etc/amavis"
        return "/etc/amavis"

    def get_daemon_name(self):
        """Return appropriate daemon name."""
        if package.backend.FORMAT == "rpm" or package.backend.FORMAT == "pkg":
            return "amavisd"
        return "amavis"

    def get_config_files(self):
        """Return appropriate config files."""
        if utils.ENV.get("debug"):
            utils.printcolor(
               "amavis.py: get_config_files",utils.YELLOW)
        if package.backend.FORMAT == "deb":
            return [
                "conf.d/05-node_id", "conf.d/15-content_filter_mode",
                "conf.d/50-user"]
        if  package.backend.FORMAT == "pkg":
            # non standard, but simpler
            # standard amavisd.conf in /usr/local/etc will not be used
            # default user is vscan, pid, sockets & homedir etc in /var/amavis
            # config_dir is set to /usr/local/etc/amavis in run.py
            new_dir = os.path.join(self.config_dir, "conf.d")
            if utils.ENV.get("debug"):
                utils.printcolor(
                   "amavis.py: creating config_dir: {}".format(new_dir),utils.YELLOW)  
            utils.exec_cmd("mkdir -p {}".format(new_dir))

            return [
                "conf.d/05-node_id", "conf.d/15-content_filter_mode",
                "conf.d/50-user", "amavisd.conf"]        

        return ["amavisd.conf"]

    def get_template_context(self):
        """Additional variables."""
        if utils.ENV.get("debug"):
            utils.printcolor(
                "amavis.py: get_template_context",utils.YELLOW)        
        context = super().get_template_context()
        context.update(
            {
                "my_home": "/var/amavis",
                # Note: $$ is 'escaping' needed for string substitute
                "lockfile": "$MYHOME/var/amavisd.lock",
                "pidfile" : "$MYHOME/var/amavisd.pid",
                "usocket": "$MYHOME/amavisd.sock",
                "user": "vscan",
                "group": "vscan"
                #"prefix": self.config.get("os","prefix")
            }
        )
        return context        
       
    def get_packages(self):
        """Additional packages."""
        if utils.ENV.get("debug"):
                utils.printcolor(
                    "amavis.py: get_packages",utils.YELLOW)
        packages = super(Amavis, self).get_packages()
        if package.backend.FORMAT == "deb":
            db_driver = "pg" if self.db_driver == "pgsql" else self.db_driver
            packages += ["libdbd-{}-perl".format(db_driver)]

            name, version = utils.dist_info()
            try:
                major_version = int(version.split(".")[0])
            except ValueError:
                major_version = 0
            if major_version >= 13:
                packages = [p if p != "liblz4-tool" else "lz4" for p in packages]
            return packages

        if self.db_driver == "pgsql":
            db_driver = "Pg"
        elif self.db_driver == "mysql":
            db_driver = "MySQL"
        else:
            raise NotImplementedError("DB driver not supported")
        if package.backend.FORMAT == "pkg":
            packages += ["p5-DBD-{}".format(db_driver)]
        else:
            packages += ["perl-DBD-{}".format(db_driver)]
        name, version = utils.dist_info()
        if version.startswith('7'):
            packages += ["cabextract", "lrzip", "unar", "unzoo"]
        elif version.startswith('8'):
            packages += ["perl-IO-stringy"]
        return packages

    def get_sql_schema_path(self):
        """Return schema path."""
        version = package.backend.get_installed_version("amavisd-new")
        if version is None:
            # Fallback to amavis...
            version = package.backend.get_installed_version("amavis")
            if version is None:
                raise utils.FatalError("Amavis is not installed")
        path = self.get_file_path(
            "amavis_{}_{}.sql".format(self.dbengine, version))
        if not os.path.exists(path):
            version = ".".join(version.split(".")[:-1]) + ".X"
            path = self.get_file_path(
                "amavis_{}_{}.sql".format(self.dbengine, version))
            if not os.path.exists(path):
                raise utils.FatalError("Failed to find amavis database schema")
        return path

    def pre_run(self):
        if utils.ENV.get("debug"):
                utils.printcolor(
                    "amavis.py: pre_run",utils.YELLOW)
        """Tasks to run first."""
        if package.backend.FORMAT != "pkg":
            with open("/etc/mailname", "w") as fp:
                fp.write("{}\n".format(self.config.get("general", "hostname")))
   

    def post_run(self):
        """Additional tasks."""
        if  package.backend.FORMAT == "pkg":
            #use config file in /usr/local/etc/amavis
            utils.exec_cmd("mv /usr/local/etc/amavisd.conf /usr/local/etc/amavisd.conf.pkg")
            utils.exec_cmd("ln -s /usr/local/etc/amavis/amavisd.conf /usr/local/etc/amavisd.conf")
            if utils.ENV.get("debug"):
                if os.path.isfile("/usr/local/etc/amavisd.conf"):
                     utils.printcolor(
                         "amavis.py: /usr/local/etc/amavisd.conf is present",utils.YELLOW)
            # update daemon for new config location and bug fix.
            utils.exec_cmd("sed -i .bak 's@/usr/local/etc/amavis.conf@/usr/local/etc/amavis/amavis.conf@' /usr/local/etc/rc.d/amavisd")
            #pidfile=${amavisd_pidfile-"/var/amavis/var/amavisd.pid"}
            utils.exec_cmd("sed -i .bak 's@/var/amavis/amavisd.pid@/var/amavis/var/amavisd.pid@' /usr/local/etc/rc.d/amavisd")
            
            
        install("spamassassin", self.config, self.upgrade, self.archive_path)
        install("clamav", self.config, self.upgrade, self.archive_path)
        # @@TODO@@  make this functional: patch to work around issue
        #file = "/usr/local/www/modoboa/env/lib/python3.11/site-packages/modoboa/calendars/serializers.py"
        #utils.exec_cmd("sed -i .bak 's@default="/etc/radicale/rights"@default="/usr/local/etc/radicale/rights"@' {}".format(file))

        

    def custom_backup(self, path):
        """Backup custom configuration if any."""
        if package.backend.FORMAT == "deb"  or package.backend.FORMAT == "pkg": 
            amavis_custom = f"{self.config_dir}/conf.d/99-custom"
            if os.path.isfile(amavis_custom):
                utils.copy_file(amavis_custom, path)
                utils.success("Amavis custom configuration saved!")
        backup("spamassassin", self.config, os.path.dirname(path))

    def restore(self):
        """Restore custom config files."""
        if package.backend.FORMAT != "deb":
            return
        amavis_custom_configuration = os.path.join(
            self.archive_path, "custom/99-custom")
        if os.path.isfile(amavis_custom_configuration):
            utils.copy_file(amavis_custom_configuration, os.path.join(
                self.config_dir, "conf.d"))
            utils.success("Custom amavis configuration restored.")
