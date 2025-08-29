import base64
import logging
import msgpack
import pyzstd

import helper

logger = logging.getLogger(__name__)


class QrData:
    def __init__(self, data=b""):
        logger.info("init qr data class")
        self.data = data
        self.enc_helper = helper.EncHelper()
        logger.debug("get salt from encryption helper")
        self.salt = self.enc_helper.get_salt()

    def serialize(self, password):
        logger.info("generate a serialized string for use in qr code")
        logger.debug("compress data")
        compressed_dat = pyzstd.compress(self.data, 16)
        base_compressed = compressed_dat
        logger.debug("set password for encryption helper")
        self.enc_helper.set_password(password)
        logger.debug("pass data to encryption helper")
        enc_msg = self.enc_helper.encrypt(base_compressed, False)
        logger.debug("generate return data with salt from e helper and encrypted data in msgpack")
        return_string = msgpack.packb({"salt": base64.b64decode(self.salt), "data": enc_msg})
        logger.debug(f"generate return string {base64.b64encode(return_string).decode("ascii")}")
        return base64.b64encode(return_string).decode("ascii")

    def get_data(self):
        logger.info("return internal data")
        return self.data

    def deserialize(self, input_string, password):
        logger.info("deserialize input data")
        logger.debug("base64 decode input and unpack with msgpack")
        input_data = msgpack.unpackb(base64.b64decode(input_string))
        logger.debug("get salt from data")
        self.salt = base64.b64encode(input_data.get(b"salt", b"")).decode("ascii")
        logger.debug("set salt and password for encryption helper")
        self.enc_helper.set_salt(self.salt)
        self.enc_helper.set_password(password)
        logger.debug("use helper to decrypt data")
        dec_msg = self.enc_helper.decrypt(input_data.get(b"data", b""), False)
        #data_to_decompress = base64.b64decode(dec_msg)
        data_to_decompress = dec_msg
        logger.debug("decompress decrypted data and store internal")
        self.data = pyzstd.decompress(data_to_decompress)

if __name__ == "__main__":
    logger.info("main of file qr_data_class")
    filename = "qr_data_class.py"
    with ((open(filename, "rb")) as f_in):
        raw_data = f_in.read()
        logger.debug(raw_data)
        qr_data = QrData(raw_data)
        logger.debug(qr_data.get_data())
        data_for_img = qr_data.serialize(password="test")
        logger.debug(data_for_img)

    input_str = ""
    logger.debug(input_str)
    qr_data_read = QrData()
    qr_data_read.deserialize(input_str, password="test")
    logger.debug(qr_data_read.get_data())
