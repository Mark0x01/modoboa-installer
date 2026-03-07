"""ClamAV related tools."""

from .. import package
from .. import utils
from .. import system

from . import base


class Clamav(base.Installer):
    """ClamAV installer."""

    appname = "clamav"
    packages = {
        "deb": ["clamav-daemon"],
        "rpm": [
            "clamav", "clamav-update", "clamav-server", "clamav-server-systemd"
        ],
        "pkg": ["clamav-lts"],
    }

    def get_daemon_name(self):
        """Return appropriate daemon name."""
        if package.backend.FORMAT == "rpm":
            return "clamd@amavisd"
        if package.backend.FORMAT == "pkg":
            return "clamav_clamd"
        return "clamav-daemon"

    @property
    def config_dir(self):
        """Return appropriate config dir."""
        if package.backend.FORMAT == "rpm":
            return "/etc"
        if package.backend.FORMAT == "pkg":
            return "/usr/local/etc"

        return ""

    def get_config_files(self):
        """Return appropriate config files."""
        if package.backend.FORMAT == "rpm":
            return ["sysconfig/clamd.amavisd", "tmpfiles.d/clamd.amavisd.conf"]
        return []

    def post_run(self):
        """Additional tasks."""
        if package.backend.FORMAT == "deb":
            user = self.config.get(self.appname, "user")
            if self.config.getboolean("amavis", "enabled"):
                system.add_user_to_group(
                    user, self.config.get("amavis", "user")
                )
            pattern = (
                "s/^AllowSupplementaryGroups false/"
                "AllowSupplementaryGroups true/")
            utils.exec_cmd(
                "perl -pi -e '{}' /etc/clamav/clamd.conf".format(pattern))
        # @TODO@
        if package.backend.FORMAT == "pkg":
            user = "clamav"
            utils.exec_cmd(
                "perl -pi -e 's/^Example/#Example/' /usr/local/etc/freshclam.conf")
            system.enable_and_start_service("clamav_clamd")

        else:
            user = "clamupdate"
            utils.exec_cmd(
                "perl -pi -e 's/^Example/#Example/' /etc/freshclam.conf")
            # Check if not present before 
            path = "/usr/lib/systemd/system/clamd@.service"
            code, output = utils.exec_cmd(
                r"grep 'WantedBy\s*=\s*multi-user.target' {}".format(path))
            if code:
                utils.exec_cmd(
                    """cat <<EOM >> {}

[Install]
WantedBy=multi-user.target
EOM
""".format(path))
        # @TODO@
        if utils.dist_name() in ["debian", "ubuntu"]:
            # Stop freshclam daemon to allow manual download
            utils.exec_cmd("service clamav-freshclam stop")
            utils.exec_cmd("freshclam", sudo_user=user, login=False)
            utils.exec_cmd("service clamav-freshclam start")
        
        else:
            utils.exec_cmd("freshclam", sudo_user=user, login=False)
