import os
import json
import tkinter as tk
from natsort import natsorted
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ExifTags

class ReceiptLabeler:
    def __init__(self, root, image_folder, output_folder):
        self.root = root
        self.image_folder = image_folder
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)

        self.images = natsorted([f for f in os.listdir(image_folder) if f.lower().endswith(".jpg")])
        self.index = 0
        self.items = []

        # Listbox gambar
        self.listbox = tk.Listbox(root, width=40, height=25)
        self.listbox.grid(row=0, column=0, rowspan=20, padx=10, pady=10, sticky="ns")
        for img in self.images:
            self.listbox.insert(tk.END, img)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_image)

        # Label gambar
        self.img_label = tk.Label(root)
        self.img_label.grid(row=0, column=1, rowspan=12, padx=10, pady=10)

        # Input metadata
        tk.Label(root, text="Invoice ID:").grid(row=0, column=2, sticky="w")
        self.invoice_entry = tk.Entry(root, width=30)
        self.invoice_entry.grid(row=0, column=3, padx=5, pady=2)

        tk.Label(root, text="Tanggal (apa adanya di struk):").grid(row=1, column=2, sticky="w")
        self.date_entry = tk.Entry(root, width=30)
        self.date_entry.grid(row=1, column=3, padx=5, pady=2)

        # Items
        tk.Label(root, text="Nama Item:").grid(row=2, column=2, sticky="w")
        self.item_name_entry = tk.Entry(root, width=30)
        self.item_name_entry.grid(row=2, column=3, padx=5, pady=2)

        tk.Label(root, text="Harga Item:").grid(row=3, column=2, sticky="w")
        self.item_price_entry = tk.Entry(root, width=30)
        self.item_price_entry.grid(row=3, column=3, padx=5, pady=2)
        self.item_price_entry.bind("<KeyRelease>", lambda e: self.format_number_entry(self.item_price_entry))

        self.add_item_btn = tk.Button(root, text="Tambah Item", command=self.add_item)
        self.add_item_btn.grid(row=3, column=4, padx=5)

        self.del_item_btn = tk.Button(root, text="Hapus Item", command=self.delete_item)
        self.del_item_btn.grid(row=3, column=5, padx=5)

        self.update_item_btn = tk.Button(root, text="Update Item", command=self.update_item)
        self.update_item_btn.grid(row=3, column=6, padx=5)

        self.items_box = tk.Listbox(root, width=40, height=6)
        self.items_box.grid(row=4, column=2, columnspan=3, pady=5)
        self.items_box.bind("<<ListboxSelect>>", self.load_selected_item) 

        # Charges fields
        self.charge_fields = {}
        charge_labels = ["service", "tax", "discount", "rounding", "tips", "delivery_fee", "other_fees"]
        for i, field in enumerate(charge_labels, start=5):
            tk.Label(root, text=f"{field.capitalize()}:").grid(row=i, column=2, sticky="w")
            entry = tk.Entry(root, width=30)
            entry.grid(row=i, column=3, padx=5, pady=2)
            entry.bind("<KeyRelease>", lambda e, ent=entry: (self.format_number_entry(ent), self.calculate_total()))
            self.charge_fields[field] = entry

        # Total 
        tk.Label(root, text="Total:").grid(row=13, column=2, sticky="w")
        self.total_entry = tk.Entry(root, width=30, state="readonly")
        self.total_entry.grid(row=13, column=3, padx=5, pady=2)

        # Buttons
        self.save_btn = tk.Button(root, text="💾 Simpan JSON", command=self.save_json)
        self.save_btn.grid(row=15, column=3, pady=5)
    
        self.prev_btn = tk.Button(root, text="<< Sebelumnya", command=self.prev_image)
        self.prev_btn.grid(row=15, column=2, pady=5)

        self.next_btn = tk.Button(root, text="Berikutnya >>", command=self.next_image)
        self.next_btn.grid(row=15, column=4, pady=5)

        self.load_image()

    # Fungsi format angka ribuan
    def format_number_entry(self, entry):
        cursor_pos = entry.index(tk.INSERT)
        val = entry.get().replace(".", "").strip()
        if not val:
            return
        try:
            num = int(val)
            formatted = f"{num:,}".replace(",", ".")
            diff = len(formatted) - len(entry.get())

            # Update isi entry
            entry.delete(0, tk.END)
            entry.insert(0, formatted)

            # Set posisi kursor kembali (supaya bisa edit tengah angka)
            new_pos = cursor_pos + diff
            if new_pos < 0:
                new_pos = 0
            elif new_pos > len(formatted):
                new_pos = len(formatted)
            entry.icursor(new_pos)
    
        except ValueError:
            pass


    @staticmethod
    def fix_orientation(img_path):
        img = Image.open(img_path)
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation, None)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except Exception as e:
            print("Exif error:", e)
        return img

    def load_image(self):
        if not self.images:
            messagebox.showerror("Error", "Folder tidak berisi file JPG")
            return

        img_path = os.path.join(self.image_folder, self.images[self.index])
        img = self.fix_orientation(img_path)
        img.thumbnail((500, 500))
        self.tk_img = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.tk_img)

        self.root.title(f"Labeling Receipt - {self.images[self.index]}")

        # Reset fields
        self.invoice_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.item_name_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.items_box.delete(0, tk.END)
        self.items = []
        for entry in self.charge_fields.values():
            entry.delete(0, tk.END)

        # Load JSON kalau sudah ada
        img_name = os.path.splitext(self.images[self.index])[0]
        json_path = os.path.join(self.output_folder, f"{img_name}.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.invoice_entry.insert(0, data.get("invoice_id", ""))
                self.date_entry.insert(0, data.get("date", ""))
                self.items = data.get("items", [])
                for item in self.items:
                    self.items_box.insert(tk.END, f"{item['name']} - {item['price']:,}".replace(",", "."))
                charges = data.get("charges", {})
                for key, entry in self.charge_fields.items():
                    entry.insert(0, f"{charges.get(key, 0):,}".replace(",", "."))
        self.calculate_total()

    def on_select_image(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.index = selection[0]
            self.load_image()

    def add_item(self):
        name = self.item_name_entry.get().strip()
        price = self.item_price_entry.get().replace(".", "").strip()
        if name and price.isdigit():
            price = int(price)
            self.items.append({"name": name, "price": price})
            self.items_box.insert(tk.END, f"{name} - {price:,}".replace(",", "."))
            self.item_name_entry.delete(0, tk.END)
            self.item_price_entry.delete(0, tk.END)
            self.calculate_total()

    def load_selected_item(self, event=None):
        selection = self.items_box.curselection()
        if not selection:
            return
        index = selection[0]
        item = self.items[index]
        # isi kembali ke entry
        self.item_name_entry.delete(0, tk.END)
        self.item_name_entry.insert(0, item["name"])
        self.item_price_entry.delete(0, tk.END)
        self.item_price_entry.insert(0, f"{item['price']:,}".replace(",", "."))

    def update_item(self):
        selection = self.items_box.curselection()
        if not selection:
            messagebox.showwarning("Peringatan", "Pilih item yang mau di-update dulu.")
            return
        index = selection[0]
        name = self.item_name_entry.get().strip()
        price = self.item_price_entry.get().replace(".", "").strip()
        if name and price.isdigit():
            price = int(price)
            self.items[index] = {"name": name, "price": price}
            self.items_box.delete(index)
            self.items_box.insert(index, f"{name} - {price:,}".replace(",", "."))
            self.items_box.selection_set(index)
            self.item_name_entry.delete(0, tk.END)
            self.item_price_entry.delete(0, tk.END)
            self.items_box.selection_clear(0, tk.END)
            self.calculate_total()
        else:
            messagebox.showwarning("Peringatan", "Nama atau harga tidak valid.")

    def delete_item(self):
        selection = self.items_box.curselection()
        if not selection:
            messagebox.showwarning("Peringatan", "Pilih item yang ingin dihapus dulu.")
            return
        index = selection[0]
        del self.items[index]
        self.items_box.delete(index)
        self.calculate_total()

    def calculate_total(self):
        total_items = sum(item["price"] for item in self.items)
        charges = {key: self.charge_fields[key].get().replace(".", "").strip() for key in self.charge_fields}
        charges = {}
        for key, entry in self.charge_fields.items():
            charges[key] = self.parse_number(entry.get())

        total = total_items + sum(charges.values())
        self.total_entry.config(state="normal")
        self.total_entry.delete(0, tk.END)
        self.total_entry.insert(0, f"{total:,}".replace(",", "."))
        self.total_entry.config(state="readonly")

        return total, charges

    def save_json(self):
        total, charges = self.calculate_total()

        data = {
            "invoice_id": self.invoice_entry.get().strip(),
            "date": self.date_entry.get().strip(),
            "items": self.items,
            "charges": charges,
            "total": total
        }

        img_name = os.path.splitext(self.images[self.index])[0]
        json_path = os.path.join(self.output_folder, f"{img_name}.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        messagebox.showinfo("Sukses", f"Data tersimpan di {json_path}")

    def next_image(self):
        if self.index < len(self.images) - 1:
            self.index += 1
            self.load_image()

    def prev_image(self):
        if self.index > 0:
            self.index -= 1
            self.load_image()

    def parse_number(self, val: str) -> int:
        val = val.replace(".", "").strip()
        if not val:
            return 0
        try:
            return int(val) 
        except ValueError:
            return 0

if __name__ == "__main__":
    root = tk.Tk()
    folder_gambar = filedialog.askdirectory(title="Pilih Folder Gambar (JPG)")
    folder_output = filedialog.askdirectory(title="Pilih Folder Output JSON")
    if folder_gambar and folder_output:
        app = ReceiptLabeler(root, folder_gambar, folder_output)
        root.mainloop()
