"""fail2ban related functions."""

from .. import package
from . import base
from .. import utils

class Fail2ban(base.Installer):
    """Fail2ban installer."""

    appname = "fail2ban"
    packages = {
        "deb": ["fail2ban"],
        "rpm": ["fail2ban"],
        "pkg": ["py311-fail2ban"]
    }

    config_files = [
      "jail.d/modoboa.conf",
      "filter.d/modoboa-auth.conf",
      ]

    @property
    def config_dir(self):
        """Add default path for FreeBSD."""
        if package.backend.FORMAT == "pkg":
            return "/usr/local/etc/fail2ban"
