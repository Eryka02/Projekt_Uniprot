import logging
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.uniprot_enzyme_explorer.charts import create_charts
from src.uniprot_enzyme_explorer.ec_classes import get_ec_class_name
from src.uniprot_enzyme_explorer.pipeline import (
    harvest_enzymes,
    load_uniprot_ids_from_files,
    parse_uniprot_ids,
)
from src.uniprot_enzyme_explorer.reports import (
    export_to_csv,
    export_to_xlsx,
)
from src.uniprot_enzyme_explorer.sequence_qc import find_duplicate_ids
from src.uniprot_enzyme_explorer.storage import (
    export_all_enzymes_to_fasta,
    export_all_nucleotide_sequences_to_fasta,
    export_non_redundant_fasta,
    export_representative_nucleotide_sequences_to_fasta,
    save_processed_records,
)
from src.uniprot_enzyme_explorer.ui_constants import (
    NUCLEOTIDE_LEGEND,
    NUCLEOTIDE_TAGS,
)
from src.uniprot_enzyme_explorer.ui_formatters import (
    build_duplicates_text,
    format_full_details,
    format_interpretation_text,
    format_nucleotide_fasta_header,
    format_protein_fasta_header,
    missing_nucleotide_message,
    table_check_status,
    wrap_sequence,
)


class UiActionsMixin:
    def _reset_display(self):
        if hasattr(self, "table"):
            for item in self.table.get_children():
                self.table.delete(item)

        self.table_count_text.set("0 rekordów")
        self.selected_enzyme = None
        self.details_title_text.set("Wybierz rekord z tabeli")
        self.details_subtitle_text.set(
            "Po kliknięciu enzymu pokażą się jego szczegóły."
        )

        for value in self.detail_values.values():
            value.set("-")

        self._set_text(
            self.interpretation_text,
            "Po pobraniu danych kliknij rekord w tabeli, aby zobaczyć interpretację.",
        )
        self._set_text(
            self.sequence_text,
            "Po pobraniu danych kliknij rekord w tabeli, aby zobaczyć sekwencje FASTA.",
        )
        self._set_text(
            self.duplicates_text,
            "Po analizie program pokaże tu powtórzone ID i grupy identycznych sekwencji.",
        )
        self._set_all_result_buttons("disabled")

    def _update_summary(self, enzymes, _total: int):
        records_count = len(enzymes)
        self.table_count_text.set(f"{records_count} rekordów")
        if self.input_duplicate_count:
            self.status_text.set(
                "Analiza zakończona. "
                f"Tabela pokazuje {records_count} unikalnych rekordów; "
                f"{self.input_duplicate_count} powtórzonych wpisów opisano "
                "w zakładce Duplikaty."
            )
        else:
            self.status_text.set("Analiza zakończona.")

    def select_input_files(self):
        selected_files = filedialog.askopenfilenames(
            parent=self.root,
            title="Wybierz pliki z identyfikatorami",
            filetypes=[
                ("Pliki tekstowe", "*.txt"),
                ("Wszystkie pliki", "*.*"),
            ],
        )

        if not selected_files:
            return

        try:
            file_paths = [
                Path(file_path)
                for file_path in selected_files
            ]

            uniprot_ids = load_uniprot_ids_from_files(file_paths)

            if not uniprot_ids:
                messagebox.showwarning(
                    "Brak identyfikatorów",
                    "Wybrane pliki nie zawierają identyfikatorów.",
                )
                return

            current_ids = parse_uniprot_ids(self.ids_text.get())
            use_existing_ids = (
                self.loaded_input_files_count > 0
                or current_ids != self.initial_input_ids
            )
            combined_ids = current_ids + uniprot_ids if use_existing_ids else uniprot_ids
            duplicate_ids = find_duplicate_ids(combined_ids)

            self.loaded_input_files_count += len(file_paths)
            self.ids_text.set(", ".join(combined_ids))
            self.status_text.set(
                f"Dodano {len(uniprot_ids)} ID z {len(file_paths)} plików. "
                f"Razem: {len(combined_ids)} ID, "
                f"unikalne: {len(set(combined_ids))}, "
                f"powtórzone wpisy: {len(combined_ids) - len(set(combined_ids))}."
            )
            if duplicate_ids:
                self._set_text(
                    self.duplicates_text,
                    "Powtórzone ID wykryte w polu wejściowym:\n"
                    + "\n".join(
                        f"- {identifier}: {count} razy"
                        for identifier, count in duplicate_ids.items()
                    ),
                )

        except OSError as error:
            logging.exception("Błąd odczytu plików.")
            messagebox.showerror("Błąd pliku", str(error))

    def start_download(self):
        uniprot_ids = parse_uniprot_ids(self.ids_text.get())

        if not uniprot_ids:
            messagebox.showwarning(
                "Brak danych",
                "Wpisz przynajmniej jeden identyfikator UniProt.",
            )
            return

        duplicate_ids = find_duplicate_ids(uniprot_ids)
        self.input_duplicate_ids = duplicate_ids
        self.input_duplicate_count = len(uniprot_ids) - len(set(uniprot_ids))
        self.unique_input_count = len(set(uniprot_ids))
        self.enzymes = []

        self._reset_display()
        self._set_all_result_buttons("disabled")
        self.download_button.configure(state="disabled")
        self.files_button.configure(state="disabled")
        self.ids_entry.configure(state="disabled")
        self.report_button.configure(state="disabled")
        self.fasta_button.configure(state="disabled")

        if duplicate_ids:
            self.status_text.set(
                f"Wykryto {self.input_duplicate_count} powtórzonych wpisów "
                f"({len(duplicate_ids)} różnych ID). "
                f"Pobieranie {self.unique_input_count} unikalnych rekordów..."
            )
        else:
            self.status_text.set(
                f"Pobieranie {self.unique_input_count} rekordów..."
            )

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
                len(set(uniprot_ids)),
            )
        except Exception as error:
            logging.exception("Błąd podczas pracy GUI.")
            self.root.after(0, self._show_error, str(error))

    def _display_results(self, enzymes, errors, total):
        self.enzymes = enzymes
        save_processed_records(enzymes)

        for item in self.table.get_children():
            self.table.delete(item)

        for index, enzyme in enumerate(enzymes):
            tag = "even" if index % 2 else "odd"
            input_count = self.input_duplicate_ids.get(enzyme.uniprot_id, 0)
            check_status = table_check_status(enzyme, input_count)

            if not enzyme.sequence:
                tag = "missing"
            elif not enzyme.is_representative:
                tag = "duplicate"
            elif input_count:
                tag = "duplicate"

            self.table.insert(
                "",
                tk.END,
                values=(
                    enzyme.uniprot_id,
                    enzyme.protein_name,
                    enzyme.organism,
                    enzyme.ec_number,
                    enzyme.sequence_length,
                    enzyme.molecular_weight,
                    enzyme.reviewed_status,
                    f"{enzyme.hydrophobic_percent}%",
                    f"{enzyme.cysteine_count} ({enzyme.cysteine_percent}%)",
                    check_status,
                ),
                tags=(tag,),
            )

        self._update_summary(enzymes, total)
        self._update_duplicates_tab()

        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        self.files_button.configure(state="normal")

        if enzymes:
            self._set_all_result_buttons("normal")
            first_item = self.table.get_children()[0]
            self.table.selection_set(first_item)
            self.table.focus(first_item)
            self._on_table_select()
        else:
            self._set_all_result_buttons("disabled")
            self._reset_details_only()
            self.status_text.set("Nie znaleziono poprawnych rekordów.")

        if errors:
            messagebox.showwarning("Niepełne wyniki", "\n".join(errors))

    def _on_table_select(self, _event=None):
        selected_item = self.table.selection()
        if not selected_item:
            self._reset_details_only()
            return

        row_index = self.table.index(selected_item[0])
        if row_index >= len(self.enzymes):
            self._reset_details_only()
            return

        enzyme = self.enzymes[row_index]
        self.selected_enzyme = enzyme
        self._update_details_panel(enzyme)
        self._update_selected_tabs(enzyme)

    def _reset_details_only(self):
        self.selected_enzyme = None
        self.details_title_text.set("Wybierz rekord z tabeli")
        self.details_subtitle_text.set(
            "Po kliknięciu enzymu pokażą się jego szczegóły."
        )
        for value in self.detail_values.values():
            value.set("-")

    def _update_details_panel(self, enzyme):
        self.details_title_text.set(enzyme.uniprot_id)
        self.details_subtitle_text.set(f"{enzyme.protein_name} | {enzyme.organism}")

        values = {
            "organism": enzyme.organism,
            "ec_number": enzyme.ec_number,
            "ec_class": get_ec_class_name(enzyme.ec_number),
            "reviewed_status": enzyme.reviewed_status,
            "sequence_length": f"{enzyme.sequence_length} aa",
            "molecular_weight": f"{enzyme.molecular_weight} Da",
            "hydrophobic": (
                f"{enzyme.hydrophobic_count} / {enzyme.hydrophobic_percent}%"
            ),
            "cysteines": f"{enzyme.cysteine_count} / {enzyme.cysteine_percent}%",
            "most_common": enzyme.most_common_amino_acid,
            "function_description": enzyme.function_description,
            "catalytic_activity": enzyme.catalytic_activity,
            "cofactors": enzyme.cofactors,
            "subcellular_location": enzyme.subcellular_location,
            "feature_summary": enzyme.feature_summary,
        }

        for key, value in values.items():
            if key in self.detail_values:
                self.detail_values[key].set(value)

    def _update_selected_tabs(self, enzyme):
        input_count = self.input_duplicate_ids.get(enzyme.uniprot_id, 0)
        self._set_text(
            self.interpretation_text,
            format_interpretation_text(enzyme, input_count),
        )
        self._set_fasta_text(enzyme)
        self._update_duplicates_tab(enzyme)

    def _set_fasta_text(self, enzyme):
        self.sequence_text.configure(state="normal")
        self.sequence_text.delete("1.0", tk.END)

        self.sequence_text.insert(
            tk.END,
            format_protein_fasta_header(enzyme) + "\n",
            ("fasta_header",),
        )
        self.sequence_text.insert(
            tk.END,
            "Sekwencja aminokwasowa:\n",
            ("sequence_note",),
        )
        self.sequence_text.insert(
            tk.END,
            wrap_sequence(enzyme.sequence) + "\n\n",
            ("protein_sequence",),
        )

        self.sequence_text.insert(
            tk.END,
            format_nucleotide_fasta_header(enzyme) + "\n",
            ("fasta_header",),
        )

        if not enzyme.nucleotide_sequence:
            self.sequence_text.insert(
                tk.END,
                missing_nucleotide_message(enzyme),
                ("sequence_note",),
            )
            self.sequence_text.configure(state="disabled")
            return

        self.sequence_text.insert(
            tk.END,
            "Sekwencja nukleotydowa:\n",
            ("sequence_note",),
        )

        for tag, label in NUCLEOTIDE_LEGEND:
            self.sequence_text.insert(tk.END, label + "\n", (tag,))

        self.sequence_text.insert(tk.END, "\n")

        for line in wrap_sequence(enzyme.nucleotide_sequence).splitlines():
            for base in line:
                tag = NUCLEOTIDE_TAGS.get(base.upper(), "base_unknown")
                self.sequence_text.insert(tk.END, base, (tag,))
            self.sequence_text.insert(tk.END, "\n")

        self.sequence_text.configure(state="disabled")

    def _update_duplicates_tab(self, selected_enzyme=None):
        text = build_duplicates_text(
            self.enzymes,
            self.input_duplicate_count,
            self.unique_input_count,
            self.input_duplicate_ids,
            selected_enzyme,
        )
        self._set_text(self.duplicates_text, text)

    def show_selected_details(self, _event=None):
        selected_item = self.table.selection()

        if not selected_item:
            messagebox.showwarning(
                "Brak wyboru",
                "Najpierw wybierz enzym z tabeli.",
            )
            return

        row_index = self.table.index(selected_item[0])
        enzyme = self.enzymes[row_index]
        input_count = self.input_duplicate_ids.get(enzyme.uniprot_id, 0)

        details_window = tk.Toplevel(self.root)
        details_window.title(f"Szczegóły enzymu {enzyme.uniprot_id}")
        details_window.geometry("780x560")
        details_window.configure(bg="#f4f7fb")

        text = tk.Text(
            details_window,
            wrap="word",
            font=("Consolas", 10),
            bg="#ffffff",
            fg="#172033",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10,
        )
        text.pack(fill="both", expand=True, padx=14, pady=14)
        text.insert("1.0", format_full_details(enzyme, input_count))
        text.configure(state="disabled")

    def _save_report(self, exporter, output_file: Path, report_name: str):
        try:
            exporter(self.enzymes, output_file, self.input_duplicate_ids)
            display_path = str(output_file)
            self.status_text.set("Raport zapisany.")
            logging.info("Zapisano raport %s: %s", report_name, output_file)
            messagebox.showinfo(
                "Raport zapisany",
                f"Utworzono raport {report_name}:\n{display_path}",
            )
        except OSError as error:
            logging.exception("Błąd zapisu raportu.")
            messagebox.showerror("Błąd zapisu", str(error))

    def save_csv(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

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
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

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

    def show_charts_window(self):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        if (
            self.charts_window is not None
            and self.charts_window.winfo_exists()
        ):
            self.charts_window.lift()
            self.charts_window.focus_force()
            return

        charts_window = tk.Toplevel(self.root)
        self.charts_window = charts_window
        charts_window.title("Wykresy")
        charts_window.geometry("1120x820")
        charts_window.minsize(900, 650)
        charts_window.configure(bg="#f4f7fb")
        charts_window.columnconfigure(0, weight=1)
        charts_window.rowconfigure(1, weight=1)

        header = ttk.Frame(charts_window, style="App.TFrame", padding=(16, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Wykresy",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Button(
            header,
            text="Zapisz wykresy",
            command=lambda: self.save_charts(charts_window),
            style="Primary.TButton",
        ).grid(row=0, column=1, sticky="e", padx=(14, 0))

        content = ttk.Frame(charts_window, style="App.TFrame", padding=(16, 0, 16, 16))
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        try:
            temp_dir = tempfile.TemporaryDirectory()
            charts_window._chart_temp_dir = temp_dir
            chart_files = list(create_charts(self.enzymes, Path(temp_dir.name)))
            self._show_chart_images(charts_window, content, chart_files)
            self.status_text.set("Wykresy wyświetlone.")
        except OSError as error:
            logging.exception("Błąd tworzenia podglądu wykresów.")
            charts_window.destroy()
            self.charts_window = None
            messagebox.showerror("Błąd wykresów", str(error))

    def _show_chart_images(self, charts_window: tk.Toplevel, parent: ttk.Frame, chart_files):
        canvas = tk.Canvas(
            parent,
            bg="#f4f7fb",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="App.TFrame")

        scroll_frame.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_canvas_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        scroll_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        charts_window._chart_images = []

        visible_charts = 0
        for index, chart_file in enumerate(chart_files):
            chart_path = Path(chart_file)

            card = ttk.Frame(scroll_frame, style="Card.TFrame", padding=12)
            card.grid(row=index, column=0, sticky="ew", pady=(0, 12))
            card.columnconfigure(0, weight=1)

            ttk.Label(
                card,
                text=chart_path.name,
                style="KpiLabel.TLabel",
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))

            try:
                image = tk.PhotoImage(file=str(chart_path))
            except tk.TclError:
                ttk.Label(
                    card,
                    text=(
                        "Tego formatu nie udało się pokazać w oknie. "
                        "Możesz zapisać wykresy przyciskiem u góry."
                    ),
                    style="KpiLabel.TLabel",
                    wraplength=720,
                ).grid(row=1, column=0, sticky="w")
                continue

            max_preview_width = 1080
            scale = max(1, (image.width() + max_preview_width - 1) // max_preview_width)
            if scale > 1:
                image = image.subsample(scale, scale)

            charts_window._chart_images.append(image)
            ttk.Label(
                card,
                image=image,
                background="#ffffff",
            ).grid(row=1, column=0)
            visible_charts += 1

        if not chart_files or visible_charts == 0:
            empty = ttk.Frame(scroll_frame, style="Card.TFrame", padding=18)
            empty.grid(row=len(chart_files), column=0, sticky="ew")
            ttk.Label(
                empty,
                text="Nie znaleziono wykresów do wyświetlenia.",
                style="KpiLabel.TLabel",
            ).grid(row=0, column=0, sticky="w")

        charts_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_charts_window(charts_window),
        )

    def _close_charts_window(self, charts_window: tk.Toplevel):
        temp_dir = getattr(charts_window, "_chart_temp_dir", None)
        charts_window.destroy()
        if self.charts_window is charts_window:
            self.charts_window = None
        if temp_dir is not None:
            temp_dir.cleanup()

    def save_charts(self, parent=None):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        dialog_parent = parent or self.root
        selected_directory = filedialog.askdirectory(
            parent=dialog_parent,
            title="Wybierz folder dla wykresów",
        )

        if not selected_directory:
            return

        try:
            chart_files = create_charts(
                self.enzymes,
                Path(selected_directory),
            )

            self.status_text.set("Wykresy zapisane.")
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

    def save_fasta(self, sequence_type: str):
        if not self.enzymes:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw pobierz dane enzymów.",
            )
            return

        if sequence_type == "nucleotide" and not any(
            record.nucleotide_sequence
            for record in self.enzymes
        ):
            messagebox.showwarning(
                "Brak sekwencji nukleotydowych",
                (
                    "Nie ma sekwencji nukleotydowych do zapisania. "
                    "UniProt musi mieć odnośnik EMBL/ENA albo RefSeq, "
                    "a aplikacja musi móc pobrać tę sekwencję."
                ),
            )
            return

        selected_directory = filedialog.askdirectory(
            parent=self.root,
            title="Wybierz folder dla plików FASTA",
        )

        if not selected_directory:
            return

        try:
            output_dir = Path(selected_directory)

            if sequence_type == "protein":
                all_sequences_file = export_all_enzymes_to_fasta(
                    self.enzymes,
                    output_dir,
                )
                representative_sequences_file = export_non_redundant_fasta(
                    self.enzymes,
                    output_dir,
                )
                sequence_label = "aminokwasowe"
            else:
                all_sequences_file = export_all_nucleotide_sequences_to_fasta(
                    self.enzymes,
                    output_dir,
                )
                representative_sequences_file = (
                    export_representative_nucleotide_sequences_to_fasta(
                        self.enzymes,
                        output_dir,
                    )
                )
                sequence_label = "nukleotydowe"

            self.status_text.set("Eksport zakończony.")
            logging.info("Zapisano pliki FASTA z poziomu GUI.")

            messagebox.showinfo(
                "FASTA zapisane",
                f"Utworzono pliki FASTA ({sequence_label}):\n"
                f"{all_sequences_file}\n"
                f"{representative_sequences_file}",
            )

        except Exception as error:
            logging.exception("Błąd zapisu FASTA.")
            messagebox.showerror("Błąd FASTA", str(error))

    def _show_error(self, message: str):
        self.status_text.set("Nie udało się pobrać danych.")
        self.download_button.configure(state="normal")
        self.ids_entry.configure(state="normal")
        self.files_button.configure(state="normal")
        self._set_all_result_buttons("disabled")
        messagebox.showerror("Błąd", message)
