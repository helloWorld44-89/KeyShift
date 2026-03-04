# QR Code Generator

Module: `app/utilities/genQR.py`

---

## `genQRCode(ssid, password=None) → str`

Generates a Wi-Fi QR code image (PNG) for the given SSID and saves it to `app/static/img/<ssidName>.png`.

The QR code encodes the standard Wi-Fi configuration string format:

```
WIFI:S:<SSID>;T:WPA;P:<password>;;
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `ssid` | `SSID` | The SSID model instance |
| `password` | `str \| None` | Override password. Defaults to `ssid.ssidPW` if not provided |

### QR Code Settings

| Setting | Value |
|---|---|
| Version | 1 (auto-fit) |
| Error correction | `ERROR_CORRECT_L` |
| Box size | 10 px |
| Border | 4 boxes |
| Fill / background | Black on white |

### Returns
- `str` — success message with the saved file path
- `str` — error message on exception
