import base64
#import json
import msgpack
import pyzstd

import helper


class QrData:
    def __init__(self, data=b""):
        self.data = data
        self.enc_helper = helper.EncHelper()
        self.salt = self.enc_helper.get_salt()

    def get_string(self, password="test"):
        compressed_dat = pyzstd.compress(self.data, 16)
        #base_compressed = base64.b64encode(compressed_dat).decode("ascii")
        base_compressed = compressed_dat
        self.enc_helper.set_password(password)
        enc_msg = self.enc_helper.encrypt(base_compressed, False)
        return_string = msgpack.packb({"salt": base64.b64decode(self.salt), "data": enc_msg})
        #print(len(return_string))
        #print(return_string)
        #print(len(base64.b64encode(return_string).decode("ascii")))
        #print(base64.b64encode(return_string).decode("ascii"))
        return base64.b64encode(return_string).decode("ascii")

    def get_data(self):
        return self.data

    def set_string(self, input_string, password="test"):
        #print(base64.b64decode(input_string))
        input_data = msgpack.unpackb(base64.b64decode(input_string))
        #print(input_data)
        self.salt = base64.b64encode(input_data.get(b"salt", b"")).decode("ascii")
        self.enc_helper.set_salt(self.salt)
        self.enc_helper.set_password(password)
        dec_msg = self.enc_helper.decrypt(input_data.get(b"data", b""), False)
        #data_to_decompress = base64.b64decode(dec_msg)
        data_to_decompress = dec_msg
        self.data = pyzstd.decompress(data_to_decompress)

if __name__ == "__main__":
    print("moin")
    filename = "test.py"
    with (open(filename, "rb")) as f_in:
        raw_data = f_in.read()
        print(raw_data)
        test = QrData(raw_data)
        print(test.get_data())
        data_for_img = test.get_string()
        print(data_for_img)

    print("-------------------------------")
    input_str = ""
    print(input_str)
    test2 = QrData()
    test2.set_string(input_str)
    print(test2.get_data())
