import pytesseract
try:
    print(pytesseract.get_tesseract_version())
except Exception as e:
    print(f"Error: {e}")
