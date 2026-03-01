"""
utils/qr.py — Generazione QR code per indirizzi di deposito.
"""
import io
import qrcode
from qrcode.image.pure import PyPNGImage


def generate_qr_bytes(address: str) -> bytes:
    """
    Genera un QR code PNG per l'indirizzo Polygon indicato.
    Restituisce i byte del PNG, pronti per send_photo di Telegram.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(address)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
