import base64
import logging
import nacl.secret
import nacl.utils
import nacl.pwhash

logger = logging.getLogger(__name__)


class EncHelper:
    def __init__(self, password="", salt=""):
        #logger.debug("init EncHelper")
        self.__password = b""
        self.__box = None
        if not salt:
            #logger.debug("generate salt")
            salt_size = nacl.pwhash.argon2i.SALTBYTES
            self.__salt = nacl.utils.random(salt_size)
        else:
            self.set_salt(salt)
        self.set_password(password)
        if self.__password and self.__salt:
            self.__gen_box()

    def __gen_box(self):
        #logger.debug("gen key with salt and password")
        kdf = nacl.pwhash.argon2i.kdf
        key = kdf(nacl.secret.SecretBox.KEY_SIZE, self.__password, self.__salt)
        self.__box = nacl.secret.SecretBox(key)

    def get_salt(self):
        #logger.debug("get salt")
        return base64.b64encode(self.__salt).decode("ascii")

    def set_salt(self, salt):
        if not isinstance(salt, str):
            #logger.error("salt not a string")
            raise TypeError("salt should be str")
        #logger.debug("set salt")
        self.__salt = base64.b64decode(salt)
        if self.__password and self.__salt:
            self.__gen_box()

    def set_password(self, password):
        if not isinstance(password, str):
            #logger.error("password not a string")
            raise TypeError("password should be str")
        #logger.debug("set password")
        self.__password = password.encode("utf-8")
        if self.__password and self.__salt:
            self.__gen_box()

    def encrypt(self, msg, encode=True):
        if not isinstance(msg, str) and not isinstance(msg, bytes):
            #logger.error("msg not a string")
            raise TypeError("msg should be str or bytes")
        if not self.__box:
            #logger.error("no key set")
            raise IOError("salt or pw not set")
        #logger.debug("encrpyt msg")
        encrypted = self.__box.encrypt(msg)
        if encode:
            return base64.b64encode(encrypted).decode("ascii")
        else:
            return encrypted

    def decrypt(self, msg, encode=True):
        if not isinstance(msg, str) and not isinstance(msg, bytes):
            #logger.error("msg not a string")
            raise TypeError("msg should be str or bytes")
        if not self.__box:
            #logger.error("no key set")
            raise IOError("salt or pw not set")
        encrypted = msg
        if isinstance(msg, str):
            encrypted = base64.b64decode(msg)
        decrypted = self.__box.decrypt(encrypted)
        if encode:
            return decrypted.decode("utf-8")
        return decrypted

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.info("moin")

    password = "moin"
    text = "test 1234"

    e1 = EncHelper()
    salt = e1.get_salt()
    logger.info("salt: {}".format(salt))
    e1.set_password(password)
    enc_msg = e1.encrypt(text)
    logger.info("e1 enc msg: {}".format(enc_msg))

    e2 = EncHelper(password)
    e2.set_salt(salt)
    dec_msg = e2.decrypt(enc_msg)
    logger.info("e2 dec msg: {}".format(dec_msg))
