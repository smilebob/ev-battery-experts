"""
GNOME Native Application for EV Battery SOH Analyzer & Certifier.
Uses GTK 4 and Libadwaita for modern GNOME look and feel.
Features:
- ViewStack multi-step flow: File Selection/Params -> Analysis Results & Charts -> Export Actions
- WebKitGTK embedded webview (or fallback if gir1.2-webkit-6.0 is not yet installed)
- Export to official signed PDF certificate (ECDSA P-256) and interactive HTML report
"""

import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

# Ensure virtualenv packages (pandas, plotly, scipy, etc.) are available if run via system Python
VENV_SITE = Path(__file__).resolve().parent / ".venv" / "lib" / "python3.14" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

# Optional WebKitGTK for interactive Plotly charts inside GNOME window
HAS_WEBKIT = False
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    HAS_WEBKIT = True
except Exception:
    HAS_WEBKIT = False

from analyzer import SOHAnalyzer, SOHResult
from chemistries import infer_pack_from_capacity
from pdf_certificate import generate_certified_pdf


class EvBatteryGnomeWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("EV Battery SOH Analyzer")
        self.set_default_size(980, 720)

        self.selected_csv_path: Optional[Path] = None
        self.last_result: Optional[SOHResult] = None
        self.last_report_path: Optional[Path] = None

        # Main layout container
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar view with HeaderBar
        self.toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(self.toolbar_view)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(self.header_bar)

        # Primary Menu Button for About / License
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu = Gio.Menu()
        menu.append("À propos de EV Battery SOH", "app.about")
        menu_button.set_menu_model(menu)
        self.header_bar.pack_end(menu_button)

        # ViewStack for step navigation
        self.view_stack = Adw.ViewStack()
        self.toolbar_view.set_content(self.view_stack)

        # ViewSwitcher in header
        self.view_switcher = Adw.ViewSwitcherTitle()
        self.view_switcher.set_stack(self.view_stack)
        self.view_switcher.set_title("EV Battery SOH")
        self.header_bar.set_title_widget(self.view_switcher)

        # Build pages
        self._build_input_page()
        self._build_results_page()

    def show_toast(self, text: str):
        toast = Adw.Toast.new(text)
        self.toast_overlay.add_toast(toast)

    # -------------------------------------------------------------
    # 1. INPUT & CONFIGURATION PAGE
    # -------------------------------------------------------------
    def _build_input_page(self):
        clamp = Adw.Clamp(maximum_size=750, tightening_threshold=550)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(16)
        box.set_margin_end(16)
        clamp.set_child(box)

        # Header status / description
        status_page = Adw.StatusPage()
        status_page.set_icon_name("battery-profile-symbolic")
        status_page.set_title("Audit Télémétrique de Santé Batterie")
        status_page.set_description(
            "Analysez vos journaux de recharge (TeslaMate, Tronity, ScanMyTesla, ABRP), "
            "calculez le SOH certifié et générez un certificat officiel infalsifiable."
        )
        box.append(status_page)

        # Preferences Group: Telemetry Source
        grp_file = Adw.PreferencesGroup()
        grp_file.set_title("Source des Données")
        grp_file.set_description("Fichier CSV exporté depuis votre enregistreur")
        box.append(grp_file)

        # File Chooser Action Row
        self.row_file = Adw.ActionRow()
        self.row_file.set_title("Fichier de Recharge CSV")
        self.row_file.set_subtitle("Aucun fichier sélectionné")

        btn_browse = Gtk.Button(label="Parcourir...")
        btn_browse.set_valign(Gtk.Align.CENTER)
        btn_browse.connect("clicked", self._on_browse_clicked)
        self.row_file.add_suffix(btn_browse)
        grp_file.add(self.row_file)

        # Preferences Group: Vehicle & Forecast Parameters
        grp_params = Adw.PreferencesGroup()
        grp_params.set_title("Paramètres du Véhicule &amp; Prévisions")
        box.append(grp_params)

        # VIN Entry Row
        self.entry_vin = Adw.EntryRow()
        self.entry_vin.set_title("Numéro de Série / VIN (Optionnel)")
        grp_params.add(self.entry_vin)

        # Annual Km Entry Row
        self.entry_annual_km = Adw.EntryRow()
        self.entry_annual_km.set_title("Rythme Kilométrique Annuel (km/an)")
        self.entry_annual_km.set_text("")
        grp_params.add(self.entry_annual_km)

        # Forecast Years Combo
        self.combo_years = Adw.ComboRow()
        self.combo_years.set_title("Horizon Prévisionnel")
        years_model = Gtk.StringList.new(["3 ans", "5 ans", "10 ans", "15 ans", "20 ans"])
        self.combo_years.set_model(years_model)
        grp_params.add(self.combo_years)

        # Language Combo
        self.combo_lang = Adw.ComboRow()
        self.combo_lang.set_title("Langue des Rapports")
        lang_model = Gtk.StringList.new(["Français (FR)", "English (EN)", "Español (ES)"])
        self.combo_lang.set_model(lang_model)
        grp_params.add(self.combo_lang)

        # Action Button: Run Analysis
        self.btn_analyze = Gtk.Button(label="Lancer l'Analyse Télémétrique")
        self.btn_analyze.add_css_class("suggested-action")
        self.btn_analyze.add_css_class("pill")
        self.btn_analyze.set_halign(Gtk.Align.CENTER)
        self.btn_analyze.set_size_request(240, 44)
        self.btn_analyze.set_margin_top(8)
        self.btn_analyze.connect("clicked", self._on_analyze_clicked)
        box.append(self.btn_analyze)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_visible(False)
        box.append(self.spinner)

        page_input = self.view_stack.add_titled(clamp, "input", "Données")
        page_input.set_icon_name("document-open-symbolic")

    def _on_browse_clicked(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Sélectionner le fichier CSV de recharge")

        # Filter for CSV
        filter_csv = Gtk.FileFilter.new()
        filter_csv.set_name("Fichiers CSV (*.csv)")
        filter_csv.add_pattern("*.csv")
        filter_csv.add_mime_type("text/csv")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_csv)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = Path(file.get_path())
                self.selected_csv_path = path
                self.row_file.set_subtitle(path.name)
        except Exception as e:
            # User cancelled or dialog error
            pass

    # -------------------------------------------------------------
    # 2. RUN ANALYSIS IN BACKGROUND THREAD
    # -------------------------------------------------------------
    def _on_analyze_clicked(self, button):
        if not self.selected_csv_path or not self.selected_csv_path.exists():
            self.show_toast("Veuillez d'abord sélectionner un fichier CSV valide.")
            return

        self.btn_analyze.set_sensitive(False)
        self.spinner.set_visible(True)
        self.spinner.start()

        # Parse inputs
        vin = self.entry_vin.get_text().strip() or None
        annual_km_str = self.entry_annual_km.get_text().strip()
        annual_km = float(annual_km_str) if annual_km_str.isdigit() else None

        years_idx = self.combo_years.get_selected()
        years_map = [3, 5, 10, 15, 20]
        forecast_years = years_map[years_idx]

        lang_idx = self.combo_lang.get_selected()
        lang_map = ["fr", "en", "es"]
        lang = lang_map[lang_idx]

        def worker():
            try:
                analyzer = SOHAnalyzer(
                    lang=lang,
                    annual_km=annual_km,
                    forecast_years=forecast_years,
                    vin=vin
                )
                df = analyzer.load_data(self.selected_csv_path)
                result = analyzer.analyze(df)

                # Generate temporary HTML report with Plotly charts
                tmp_dir = Path(tempfile.gettempdir()) / "ev_battery_soh_gnome"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                report_path = tmp_dir / f"report_{result.analysis_date.strftime('%Y%m%d_%H%M%S')}.html"
                analyzer.generate_html_report(result, report_path)

                GLib.idle_add(self._on_analysis_success, result, report_path, lang)
            except Exception as e:
                GLib.idle_add(self._on_analysis_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_success(self, result: SOHResult, report_path: Path, lang: str):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.btn_analyze.set_sensitive(True)

        self.last_result = result
        self.last_report_path = report_path

        self._update_results_ui(result, report_path, lang)
        self.view_stack.set_visible_child_name("results")
        self.show_toast("Analyse de dégradation terminée avec succès !")

    def _on_analysis_error(self, err_msg: str):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.btn_analyze.set_sensitive(True)
        self.show_toast(f"Erreur lors de l'analyse : {err_msg}")

    # -------------------------------------------------------------
    # 3. RESULTS & CHARTS PAGE
    # -------------------------------------------------------------
    def _build_results_page(self):
        box_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Action bar at top of results
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_bar.set_margin_top(12)
        top_bar.set_margin_bottom(12)
        top_bar.set_margin_start(16)
        top_bar.set_margin_end(16)

        self.lbl_veh_title = Gtk.Label(label="Véhicule Audité")
        self.lbl_veh_title.add_css_class("title-3")
        self.lbl_veh_title.set_hexpand(True)
        self.lbl_veh_title.set_halign(Gtk.Align.START)
        top_bar.append(self.lbl_veh_title)

        btn_pdf = Gtk.Button(label="Certificat PDF Signé")
        btn_pdf.set_icon_name("document-save-symbolic")
        btn_pdf.add_css_class("suggested-action")
        btn_pdf.connect("clicked", self._on_export_pdf_clicked)
        top_bar.append(btn_pdf)

        btn_browser = Gtk.Button(label="Ouvrir dans le Navigateur")
        btn_browser.set_icon_name("web-browser-symbolic")
        btn_browser.connect("clicked", self._on_open_browser_clicked)
        top_bar.append(btn_browser)

        box_main.append(top_bar)

        # KPI Badges Grid
        kpi_clamp = Adw.Clamp(maximum_size=920)
        self.kpi_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.kpi_box.set_homogeneous(True)
        self.kpi_box.set_margin_bottom(12)
        self.kpi_box.set_margin_start(16)
        self.kpi_box.set_margin_end(16)
        kpi_clamp.set_child(self.kpi_box)

        # 4 KPI cards
        self.card_soh = self._create_kpi_card("SOH Actuel", "-- %", "Marge d'erreur : ± -- %")
        self.card_cap = self._create_kpi_card("Capacité Résiduelle", "-- kWh", "Référence C₀ : -- kWh")
        self.card_sessions = self._create_kpi_card("Recharges Validées", "--", "Dont -- % en DC rapide")
        self.card_odo = self._create_kpi_card("Kilométrage", "-- km", "Rythme : -- km/an")

        self.kpi_box.append(self.card_soh)
        self.kpi_box.append(self.card_cap)
        self.kpi_box.append(self.card_sessions)
        self.kpi_box.append(self.card_odo)

        box_main.append(kpi_clamp)

        # WebView or Fallback Banner for charts
        if HAS_WEBKIT:
            self.webview = WebKit.WebView()
            self.webview.set_hexpand(True)
            self.webview.set_vexpand(True)
            box_main.append(self.webview)
        else:
            fallback = Adw.StatusPage()
            fallback.set_icon_name("utilities-system-monitor-symbolic")
            fallback.set_title("Rapport Interactif & Graphiques Prêts")
            fallback.set_description(
                "Le paquet système 'gir1.2-webkit-6.0' n'est pas encore installé pour l'affichage interne WebKit.\n"
                "Vous pouvez consulter l'ensemble des graphiques interactifs en cliquant sur 'Ouvrir dans le Navigateur'."
            )
            fallback.set_vexpand(True)
            box_main.append(fallback)

        page_results = self.view_stack.add_titled(box_main, "results", "Résultats")
        page_results.set_icon_name("utilities-system-monitor-symbolic")

    def _create_kpi_card(self, title: str, val: str, sub: str) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(14)
        box.set_margin_end(14)

        lbl_t = Gtk.Label(label=title)
        lbl_t.add_css_class("caption")
        lbl_t.add_css_class("dim-label")
        lbl_t.set_halign(Gtk.Align.START)

        lbl_v = Gtk.Label(label=val)
        lbl_v.add_css_class("title-2")
        lbl_v.set_halign(Gtk.Align.START)

        lbl_s = Gtk.Label(label=sub)
        lbl_s.add_css_class("caption")
        lbl_s.set_halign(Gtk.Align.START)

        box.append(lbl_t)
        box.append(lbl_v)
        box.append(lbl_s)
        frame.set_child(box)

        # Store references to labels
        frame.lbl_title = lbl_t
        frame.lbl_val = lbl_v
        frame.lbl_sub = lbl_s
        return frame

    def _update_results_ui(self, result: SOHResult, report_path: Path, lang: str):
        pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)
        vin_str = f" • VIN: {result.vin}" if result.vin else ""
        self.lbl_veh_title.set_label(f"{pack_info.make} {pack_info.model} {pack_info.variant}{vin_str}")

        # Update KPI cards
        self.card_soh.lbl_val.set_label(f"{result.current_soh:.2f} %")
        self.card_soh.lbl_sub.set_label(f"± {result.current_soh_err:.2f} % (IC 95%)")

        self.card_cap.lbl_val.set_label(f"{result.current_capacity:.2f} kWh")
        self.card_cap.lbl_sub.set_label(f"C₀ : {result.initial_capacity:.2f} kWh")

        self.card_sessions.lbl_val.set_label(str(result.qualified_charges))
        self.card_sessions.lbl_sub.set_label(f"{result.dc_energy_pct:.1f}% charge DC")

        self.card_odo.lbl_val.set_label(f"{result.odometer_max:,.0f} km")
        self.card_odo.lbl_sub.set_label(f"~{result.annual_km:,.0f} km/an")

        # Load interactive HTML report in embedded WebKit view if available
        if HAS_WEBKIT:
            self.webview.load_uri(f"file://{report_path.resolve()}")

    def _on_open_browser_clicked(self, button):
        if self.last_report_path and self.last_report_path.exists():
            Gio.AppInfo.launch_default_for_uri(f"file://{self.last_report_path.resolve()}", None)
        else:
            self.show_toast("Aucun rapport disponible.")

    def _on_export_pdf_clicked(self, button):
        if not self.last_result:
            self.show_toast("Veuillez d'abord exécuter une analyse.")
            return

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Enregistrer le certificat d'inspection PDF officiel")
        default_name = f"certificat_soh_{self.last_result.analysis_date.strftime('%Y%m%d')}.pdf"
        dialog.set_initial_name(default_name)

        # Filter for PDF
        filter_pdf = Gtk.FileFilter.new()
        filter_pdf.set_name("Documents PDF (*.pdf)")
        filter_pdf.add_pattern("*.pdf")
        filter_pdf.add_mime_type("application/pdf")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_pdf)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_pdf_save_selected)

    def _on_pdf_save_selected(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file and self.last_result:
                out_path = Path(file.get_path())
                pack_key, pack_info = infer_pack_from_capacity(self.last_result.initial_capacity)
                v_info = {
                    "make": pack_info.make,
                    "model": f"{pack_info.model} {pack_info.variant}",
                    "chemistry": pack_info.chemistry.name
                }
                lang = ["fr", "en", "es"][self.combo_lang.get_selected()]

                generate_certified_pdf(
                    result=self.last_result,
                    csv_file=self.selected_csv_path,
                    output_pdf_path=out_path,
                    vehicle_info=v_info,
                    lang=lang,
                    vin=self.last_result.vin
                )
                self.show_toast(f"Certificat PDF enregistré : {out_path.name}")
        except Exception as e:
            self.show_toast(f"Erreur d'enregistrement PDF : {e}")


class EvBatteryGnomeApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.smilebob.EvBatterySoh",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_activated)
        self.add_action(about_action)

    def _on_about_activated(self, action, param):
        win = self.props.active_window
        dialog = Adw.AboutDialog()
        dialog.set_application_name("EV Battery SOH")
        dialog.set_application_icon("org.smilebob.EvBatterySoh")
        dialog.set_developer_name("Pierre Roth (smilebob)")
        dialog.set_version("0.2.0")
        dialog.set_copyright("© 2026 Pierre Roth")
        dialog.set_license_type(Gtk.License.BSD_3)
        dialog.set_website("https://github.com/smilebob/ev-battery-experts")
        dialog.set_issue_url("https://github.com/smilebob/ev-battery-experts/issues")
        dialog.set_comments(
            "Analyseur de dégradation et de santé de batterie (SOH) pour véhicules électriques.\n"
            "Régression locale LOWESS (IC 95%), cinétique thermique d'Arrhenius, "
            "projections multi-scénarios et certificats PDF signés par clé asymétrique ECDSA P-256."
        )
        dialog.present(win)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = EvBatteryGnomeWindow(application=self)
        win.present()


def main():
    app = EvBatteryGnomeApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
