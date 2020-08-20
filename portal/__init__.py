from common import utils
from django.core import mail

__version__ = "0.1.0"
__version_info__ = tuple(
    [int(num) if num.isdigit() else num for num in __version__.replace("-", ".", 1).split(".")]
)

mail.send_mail = utils.send_mail
