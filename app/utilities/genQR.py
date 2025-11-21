import qrcode


def genQRCode(password):
   
    ssid='ThouShaltNotSteal'
    security_type="WPA"
    hidden=False
    filename="guestqrcode.png"
    # Construct the Wi-Fi configuration string in the standard format
    # WIFI:S:<SSID>;T:<security_type>;P:<password>;H:<hidden_status>;
    wifi_data = f"WIFI:S:{ssid};T:{security_type};P:{password};"
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
    img.save(f"app/static/img/{filename}")
    return(f"QR code saved as {filename}")

