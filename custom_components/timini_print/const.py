"""Constants for the TiMini Print integration."""

DOMAIN = "timini_print"

DEFAULT_PORT = 8096

SERVICE_PRINT_TEXT = "print_text"
SERVICE_PRINT_IMAGE = "print_image"
SERVICE_PRINT_IMAGE_DATA = "print_image_data"
SERVICE_SCAN = "scan"
SERVICE_LIST_MODELS = "list_models"
SERVICE_LIST_HA_BLUETOOTH_DEVICES = "list_ha_bluetooth_devices"

ATTR_MESSAGE = "message"
ATTR_PRINTER = "printer"
ATTR_FILE_PATH = "file_path"
ATTR_IMAGE_B64 = "image_b64"
ATTR_FILENAME = "filename"
ATTR_TEXT_COLUMNS = "text_columns"
ATTR_DARKNESS = "darkness"
ATTR_PRINTER_MODEL = "printer_model"

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf"}
