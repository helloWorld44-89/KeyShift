import qrcode
from ..config import config
import os
from ..models import SSID
import logging

log = logging.getLogger("utilities.genQR")

def genQRCode(ssid:SSID,password):
    try:
        BASE_DIR = os.path.abspath(os.path.dirname("static")) 
        imgPath = os.path.join("/app","app","static","img") 
        security_type="WPA"
        hidden=False
        filename=f"{ssid.ssidName}.png"
        # Construct the Wi-Fi configuration string in the standard format
        # WIFI:S:<SSID>;T:<security_type>;P:<password>;H:<hidden_status>;
        wifi_data = f"WIFI:S:{ssid.ssidName};T:{security_type};P:{password};"
        if hidden:
            wifi_data += "H:true;"
        wifi_data += ";"

        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Add the Wi-Fi data to the QR code
        qr.add_data(wifi_data)
        qr.make(fit=True)

        # Create an image from the QR code instance
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image
        img.save(f"{imgPath}/{filename}")
        log.info(f"QR Saved: {imgPath}/{filename}")
        return(f"QR code saved as {filename}")
    except Exception as e:
        log.error(f"Error: {e}")
        log.debug(f"Error: {e} | Params: {password}; WifiData: {wifi_data}")
