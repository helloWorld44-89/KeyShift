import qrcode
from ..config import config
import os
from ..models import SSID
import logging

log = logging.getLogger("utilities.genQR")


def genQRCode(ssid: SSID, password: str = None) -> str:
    """
    Generate a Wi-Fi QR code image (PNG) for the given SSID.

    Encodes the standard Wi-Fi configuration string:
        WIFI:S:<SSID>;T:WPA;P:<password>;;

    The generated image is saved to app/static/img/<ssidName>.png,
    where it is served by the /qr/<id> route.

    Args:
        ssid: The SSID model instance to generate the QR code for.
        password: Override the password embedded in the QR code.
                  Defaults to ssid.ssidPW if not provided.

    Returns:
        A success message string with the saved file path,
        or an error message string on failure.
    """
    try:
        BASE_DIR = os.path.abspath(os.path.dirname("static"))
        imgPath = os.path.join(BASE_DIR, "app", "static", "img")
        security_type = "WPA"  # WPA/WPA2/WPA3 — covers all modern networks
        hidden = False
        filename = f"{ssid.ssidName}.png"

        # Use the SSID's stored password if no override is provided
        if password is None:
            password = ssid.ssidPW

        # Build the Wi-Fi QR code payload (mecard-like format)
        # Spec: https://github.com/zxing/zxing/wiki/Barcode-Contents#wi-fi-network-config-android
        wifi_data = f"WIFI:S:{ssid.ssidName};T:{security_type};P:{password};"
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
        img.save(f"{imgPath}/{filename}")

        log.info(f"QR Saved: {imgPath}/{filename}")
        return (f"QR code saved as {filename}")
    except Exception as e:
        log.error(f"Error: {e}")
        log.debug(f"Error: {e} | Params: {password}; WifiData: {wifi_data}")
