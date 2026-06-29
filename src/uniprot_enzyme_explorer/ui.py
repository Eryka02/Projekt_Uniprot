import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.uniprot_enzyme_explorer.charts import create_charts
from src.uniprot_enzyme_explorer.pipeline import (
    harvest_enzymes,
    load_uniprot_ids,
    parse_uniprot_ids,
)
from src.uniprot_enzyme_explorer.reports import (
    export_to_csv,
    export_to_xlsx,
)


class EnzymeExplorerApp:
    def __init__(
        self,
        root: tk.Tk,
        project_root: Path,
        input_file: Path,
    ):
        self.root = root
        self.project_root = project_root
        self.input_file = input_file
        self.enzymes = []

        self.root.title("UniProt Enzyme Explorer")
        self.root.geometry("1150x600")
        self.root.minsize(900, 480)

        self._build_interface()

    def _build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        style = ttk.Style()
        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure("Treeview", rowheight=26)

        title = ttk.Label(
            main_frame,
            text="UniProt Enzyme Explorer",
            style="Title.TLabel",
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        try:
            initial_ids = load_uniprot_ids(self.input_file)
        except OSError:
            initial_ids = []

        self.ids_text = tk.StringVar(
            value=", ".join(initial_ids)
        )

        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(
            input_frame,
            text="Identyfikatory UniProt:",
        ).grid(row=0, column=0, padx=(0, 8))

        self.ids_entry = ttk.Entry(
            input_frame,
            textvariable=self.ids_text,
        )
        self.ids_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 8),
        )

        self.download_button = ttk.Button(
            input_frame,
            text="Pobierz dane",
            command=self.start_download,
        )
        self.download_button.grid(row=0, column=2)

        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, sticky="w", pady=(0, 10))

        self.csv_button = ttk.Button(
            action_frame,
            text="Zapisz CSV",
            command=self.save_csv,
            state="disabled",
        )
        self.csv_button.grid(row=0, column=0, padx=(0, 6))

        self.xlsx_button = ttk.Button(
            action_frame,
            text="Zapisz XLSX",
            command=self.save_xlsx,
            state="disabled",
        )
        self.xlsx_button.grid(row=0, column=1, padx=(0, 6))

        self.charts_button = ttk.Button(
            action_frame,
            text="Utwórz wykresy",
            command=self.save_charts,
            state="disabled",
        )
        self.charts_button.grid(row=0, column=2)

        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "id",
            "name",
            "organism",
            "length",
            "mass",
            "ec",
            "sequence",
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )

        settings = {
            "id": ("ID UniProt", 100),
            "name": ("Nazwa białka", 230),
            "organism": ("Organizm", 150),
            "length": ("Długość", 90),
            "mass": ("Masa [Da]", 100),
            "ec": ("Numer EC", 100),
            "sequence": ("Sekwencja", 230),
        }

        for column, (heading, width) in settings.items():
            self.table.heading(column, text=heading)
            self.table.column(column, width=width, minwidth=80)

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.table.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.table.xview,
        )

        self.table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.status_text = tk.StringVar(
            value="Gotowe do pobrania danych."
        )

        ttk.Label(
            main_frame,
            textvariable=self.status_text,
        ).grid(row=4, column=0, sticky="w", pady=(10, 0))

    def _set_report_buttons(self, state: str):
        self.csv_button.configure(state=state)
        self.xlsx_button.configure(state=state)
        self.charts_button.configure(state=state)

    def start_download(self):
        uniprot_ids = parse_uniprot_ids(self.ids_text.get())

        if not uniprot_ids:
            messagebox.showwarning(
                "Brak danych",
                "Wpisz przynajmniej jeden identyfikator UniProt.",
            )
            return

        self.enzymes = []
        self._set_report_buttons("disabled")
        self.download_button.configure(state="disabled")
        self.ids_entry.configure(state="disabled")
        self.status_text.set(f"Pobieranie rekordów: {len(uniprot_ids)}...")

        for item in self.table.get_children():
            self.table.delete(item)

        threading.Thread(
            target=self._download_data,
            args=(uniprot_ids,),
            daemon=True,
        ).start()

    def _download_data(self, uniprot_ids):
        try:
            enzymes, errors = harvest_enzymes(uniprot_ids)
            self.root.after(
                0,
                self._display_results,
                enzymes,
                errors,
                len(uniprot_ids),
            )
        except Exception as error:
            logging.exception("Błąd podczas pracy GUI.")
            self.root.after(0, self._show_error, str(error))

    def _display_results(self, enzymes, errors, total):
        self.enzymes = enzymes

        for enzyme in enzymes:
            sequence = enzyme.sequence[:35]

            if len(enzyme.sequence) > 35:
                sequence += "..."

            self.table.insert(
                "",
                tk.END,
                values=(
                    enzyme.uniprot_id,
                    enzyme.protein_name,
                    enzyme.organism,
                    enzyme.sequence_length,
                    enzyme.molecular_weight,
                    enzyme.ec_number,
                    sequence,
                ),
            )

        self.status_text.set(f"Pobrano poprawnie: {len(enzymes)} z {total}.")
        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")

        if enzymes:
            self._set_report_buttons("normal")

        if errors:
            messagebox.showwarning("Niepełne wyniki", "\n".join(errors))

    def _save_report(self, exporter, output_file: Path, report_name: str):
        try:
            exporter(self.enzymes, output_file)
            display_path = str(output_file)
            self.status_text.set(f"Zapisano raport: {display_path}")
            logging.info("Zapisano raport %s: %s", report_name, output_file)
            messagebox.showinfo(
                "Raport zapisany",
                f"Utworzono raport {report_name}:\n{display_path}",
            )
        except OSError as error:
            logging.exception("Błąd zapisu raportu.")
            messagebox.showerror("Błąd zapisu", str(error))

    def save_csv(self):
        selected_file = filedialog.asksaveasfilename(
            parent=self.root,
            title="Zapisz raport CSV",
            defaultextension=".csv",
            initialfile="enzyme_report.csv",
            filetypes=[("Pliki CSV", "*.csv")],
        )

        if not selected_file:
            return

        self._save_report(
            export_to_csv,
            Path(selected_file),
            "CSV",
        )

    def save_xlsx(self):
        selected_file = filedialog.asksaveasfilename(
            parent=self.root,
            title="Zapisz raport XLSX",
            defaultextension=".xlsx",
            initialfile="enzyme_report.xlsx",
            filetypes=[("Pliki Excel", "*.xlsx")],
        )

        if not selected_file:
            return

        self._save_report(
            export_to_xlsx,
            Path(selected_file),
            "XLSX",
        )

    def save_charts(self):
        selected_directory = filedialog.askdirectory(
            parent=self.root,
            title="Wybierz folder dla wykresów",
        )

        if not selected_directory:
            return

        try:
            chart_files = create_charts(
                self.enzymes,
                Path(selected_directory),
            )

            self.status_text.set("Utworzono wykresy.")
            logging.info("Utworzono wykresy z poziomu GUI.")

            file_names = "\n".join(
                str(path)
                for path in chart_files
            )

            messagebox.showinfo(
                "Wykresy utworzone",
                f"Zapisano wykresy:\n{file_names}",
            )

        except OSError as error:
            logging.exception("Błąd tworzenia wykresów.")
            messagebox.showerror("Błąd wykresów", str(error))

    def _show_error(self, message: str):
        self.status_text.set("Nie udało się pobrać danych.")
        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        messagebox.showerror("Błąd", message)





