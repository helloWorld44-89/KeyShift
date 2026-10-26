import qrcode
import os
from flask import current_app
from werkzeug.utils import secure_filename
from ..models import SSID
import logging

log = logging.getLogger("utilities.genQR")


def qrDir() -> str:
    """
    Directory holding generated QR images.

    Lives under the instance folder (a mounted volume), NOT under static/,
    so the images are only reachable through the routes that check access.
    """
    path = current_app.config.get("QR_DIR") or os.path.join(current_app.instance_path, "qr")
    os.makedirs(path, exist_ok=True)
    return path


def qrPath(ssid: SSID) -> str:
    """Absolute path of the QR image for an SSID, keyed by its controller ID."""
    return os.path.join(qrDir(), secure_filename(f"{ssid.ssidID}.png"))


def escapeWifi(value: str) -> str:
    """Backslash-escape the characters that are special in the WIFI: QR format."""
    for ch in ('\\', ';', ',', ':', '"'):
        value = value.replace(ch, '\\' + ch)
    return value


def genQRCode(ssid: SSID, password: str = None) -> str:
    """
    Generate a Wi-Fi QR code image (PNG) for the given SSID.

    Encodes the standard Wi-Fi configuration string:
        WIFI:S:<SSID>;T:WPA;P:<password>;;

    The generated image is saved under the instance folder (see qrPath) and
    served by the /qr/<id> and /api/guest routes.

    Args:
        ssid: The SSID model instance to generate the QR code for.
        password: Override the password embedded in the QR code.
                  Defaults to ssid.ssidPW if not provided.

    Returns:
        A success message string with the saved file path,
        or an error message string on failure.
    """
    try:
        security_type = "WPA"  # WPA/WPA2/WPA3 — covers all modern networks
        hidden = False
        imgPath = qrPath(ssid)

        # Use the SSID's stored password if no override is provided
        if password is None:
            password = ssid.ssidPW

        # Build the Wi-Fi QR code payload (mecard-like format); SSID and password
        # must have \\ ; , : " escaped or scanners misread them
        # Spec: https://github.com/zxing/zxing/wiki/Barcode-Contents#wi-fi-network-config-android
        wifi_data = f"WIFI:S:{escapeWifi(ssid.ssidName)};T:{security_type};P:{escapeWifi(password)};"
        if hidden:
            wifi_data += "H:true;"
        wifi_data += ";"  # Double semicolon terminates the record

        # Configure QR code parameters
        qr = qrcode.QRCode(
            version=1,                                  # Version 1 = 21x21 modules; auto-grows with fit=True
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # ~7% error correction (sufficient for screen display)
            box_size=10,                                # Pixels per module
            border=4,                                   # Quiet zone (4 modules is the minimum per spec)
        )

        qr.add_data(wifi_data)
        qr.make(fit=True)  # Automatically increase version if data doesn't fit

        # Render and save as PNG
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(imgPath)

        log.info(f"QR Saved: {imgPath}")
        return (f"QR code saved as {imgPath}")
    except Exception as e:
        log.error(f"Error: {e}")
        log.debug(f"Error generating QR for {ssid.ssidName}", exc_info=True)
