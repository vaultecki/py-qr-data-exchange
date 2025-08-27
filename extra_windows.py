import math
import tkinter
import io
from tkinter import filedialog, messagebox

import qr_data_class


class QrWindow:
    def __init__(self, qr_code_generated, qr_code_text):
        self.qr_window = tkinter.Tk()
        self.qr_window.title("New Window")

        tkinter.Label(self.qr_window, text="Qr Code wurde generiert:").grid(row=0, column=0)
        var_qr_code_text = tkinter.StringVar(self.qr_window, qr_code_text)
        tkinter.Entry(self.qr_window, width=60, textvariable=var_qr_code_text, state="readonly").grid(row=0, column=1)

        self.qr_code_generated = qr_code_generated

        maxsize = math.floor((min(self.qr_window.winfo_screenwidth(), self.qr_window.winfo_screenheight()))*0.8)
        resize_image = qr_code_generated.resize((maxsize, maxsize))

        output = io.BytesIO()
        resize_image.save(output, format='PNG')

        self.image_qr = tkinter.PhotoImage(data=output.getvalue(), master=self.qr_window)
        self.tkinter_qr = tkinter.Label(master=self.qr_window, image=self.image_qr)
        self.tkinter_qr.grid(row=1, column=0, columnspan=2)

        self.button = tkinter.Button(master=self.qr_window, text="Save As", command=self.save_file)
        self.button.grid(row=2, column=0, columnspan=2)

        self.qr_window.mainloop()

    def save_file(self):
        file_out = filedialog.asksaveasfilename()
        if file_out:
            self.qr_code_generated.save("{}".format(file_out))


class ReadWindow:
    def __init__(self, password, qr_text=""):
        print("moin")
        self.password = password
        self.read_window = tkinter.Tk()
        self.read_window.title("New Window")

        tkinter.Label(self.read_window, text="Text to convert:").grid(row=0, column=0, padx=5, pady=5)
        if qr_text:
            text = tkinter.StringVar(self.read_window, qr_text)
            self.text_field = tkinter.Entry(self.read_window, textvariable=text, width=60, state="readonly")
        else:
            self.text_field = tkinter.Entry(self.read_window, width=60)
        self.text_field.grid(row=0, column=1)

        tkinter.Button(self.read_window, text="Decrypt and Save as", command=self.save_as).grid(row=1, column=1, padx=5, pady=5)

        self.read_window.mainloop()

    def save_as(self):
        qr_data = qr_data_class.QrData()
        qr_data.set_string(self.text_field.get(), password=self.password)
        # print(qr_data.get_data())
        file_out = filedialog.asksaveasfilename()
        if file_out:
            with (open(file_out, "wb+")) as f_out:
                f_out.write(qr_data.get_data())


if __name__ == "__main__":
    print("moin")
