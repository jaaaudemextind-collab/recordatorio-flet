import flet as ft
import json
import os
import re
import asyncio
from datetime import datetime

DB_FILE = "datos_academia.json"

def main(page: ft.Page):
    # --- CONFIGURACIÓN DE VENTANA ---
    page.title = "Panel Académico TI"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a" 
    page.padding = 20
    page.window.width = 450
    page.window.height = 850
    page.scroll = ft.ScrollMode.ADAPTIVE

    filtro_activo = {"tipo": "todos", "valor": None}

    def cargar_datos():
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "historial_completadas" not in data: data["historial_completadas"] = {}
                    return data
            except: pass
        return {"materias": ["Cloud computing", "Base de Datos", "Backend Python"], 
                "entregas": [], "completadas_count": 0, "historial_completadas": {}}

    state = cargar_datos()
    tarea_editando = {"ref": None}

    lista_tareas_ui = ft.Column(spacing=12)
    dashboard_ui = ft.Row(wrap=True, spacing=10)
    pb_barra = ft.ProgressBar(height=8, border_radius=5, color="#f59e0b", bgcolor="#1e293b", value=0)
    txt_pct = ft.Text("0% Completado", size=12, weight="bold", color="#f59e0b")
    txt_titulo_lista = ft.Text("Pendientes Críticos", size=16, weight="bold", expand=True)
    
    def guardar_y_refrescar():
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        renderizar_tareas()
        actualizar_progreso()
        actualizar_dashboard()
        dd_materia.options = [ft.dropdown.Option(m) for m in state["materias"]]
        page.update()

    def actualizar_progreso():
        pend = len(state["entregas"])
        comp = state.get("completadas_count", 0)
        total = pend + comp
        val = comp / total if total > 0 else 0
        pb_barra.value = val
        txt_pct.value = f"{int(val*100)}% de avance académico"
        page.update()

    def filtrar_por_materia(materia_nombre):
        filtro_activo["tipo"] = "materia"
        filtro_activo["valor"] = materia_nombre
        sb_filtros.selected = {"materia_btn"} 
        renderizar_tareas()

    def actualizar_dashboard():
        dashboard_ui.controls = []
        historial = state.get("historial_completadas", {})
        for mat_dash, count in historial.items(): # Cambio de nombre para evitar conflictos
            if count > 0:
                dashboard_ui.controls.append(
                    ft.Container(
                        content=ft.Text(f"{mat_dash}: {count}", size=10, weight="bold", color="#f59e0b" if filtro_activo["valor"] == mat_dash else "#94a3b8"),
                        bgcolor="#1e293b", padding=8, border_radius=8, 
                        border=ft.border.all(1, "#f59e0b" if filtro_activo["valor"] == mat_dash else "#334155"),
                        on_click=lambda _, m=mat_dash: filtrar_por_materia(m)
                    )
                )
        page.update()

    def obtener_tiempo_restante(fecha_str):
        try:
            anio_actual = datetime.now().year
            fecha_meta = datetime.strptime(f"{fecha_str} {anio_actual}", "%d/%m %H:%M %Y")
            ahora = datetime.now()
            diff = fecha_meta - ahora
            segundos = diff.total_seconds()
            if segundos < 0: return "⚠️ Vencida", "#ef4444", False, segundos
            dias = diff.days
            horas = diff.seconds // 3600
            mins = (diff.seconds % 3600) // 60
            urgente = segundos < 7200
            if dias > 0: return f"Faltan {dias}d {horas}h", "#94a3b8", urgente, segundos
            if horas > 0: return f"En {horas}h {mins}m", "#fbbf24", urgente, segundos
            return f"En {mins} min", "#f59e0b", urgente, segundos
        except: return "Pendiente", "#64748b", False, 999999

    def iniciar_edicion(entrega):
        tarea_editando["ref"] = entrega
        dd_materia.value = entrega["materia"]
        dd_prio.value = entrega["prio"]
        txt_act.value = entrega["actividad"]
        txt_fec.value = entrega["fecha"]
        btn_registrar.text = "Actualizar"
        btn_registrar.bgcolor = ft.Colors.BLUE_700
        btn_registrar.icon = ft.Icons.EDIT_NOTE
        page.update()

    def crear_card_tarea(entrega):
        prio_conf = {"Crítica": "#ef4444", "Media": "#f59e0b", "Baja": "#3b82f6"}
        conf_color = prio_conf.get(entrega.get("prio", "Media"), "#f59e0b")
        txt_tiempo, color_tiempo, es_urgente, _ = obtener_tiempo_restante(entrega['fecha'])

        card = ft.Container(
            content=ft.Row([
                ft.Container(width=5, bgcolor=conf_color, border_radius=5, height=60),
                ft.Row([
                    ft.Column([
                        ft.Text(entrega['materia'], weight="bold", size=14, no_wrap=False),
                        ft.Text(entrega['actividad'], size=13, color="#94a3b8", no_wrap=False),
                        ft.Row([
                            ft.Text(f"📅 {entrega['fecha']}", size=11, color="#f8fafc"),
                            ft.Text(txt_tiempo, size=11, weight="bold", color=color_tiempo)
                        ], spacing=10)
                    ], spacing=2, expand=True), # Expand ayuda a que el texto ocupe su lugar
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color="#94a3b8", on_click=lambda _: iniciar_edicion(entrega)),
                        ft.IconButton(icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, icon_color="#10b981", on_click=lambda _: completar_tarea(entrega))
                    ], spacing=0)
                ], expand=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e293b", border_radius=12, border=ft.border.all(1, "#334155"), 
            padding=12,
            animate_opacity=300 if es_urgente else 0
        )

        if es_urgente:
            async def blink():
                while True:
                    try:
                        card.opacity = 0.5 if card.opacity == 1 else 1
                        card.update()
                        await asyncio.sleep(0.8)
                    except: break
            page.run_task(blink)
        return card

    def completar_tarea(entrega):
        m = entrega["materia"]
        state["historial_completadas"][m] = state["historial_completadas"].get(m, 0) + 1
        state["entregas"].remove(entrega)
        state["completadas_count"] = state.get("completadas_count", 0) + 1
        guardar_y_refrescar()

    def cambiar_filtro(e):
        filtro_activo["tipo"] = list(e.selection)[0]
        filtro_activo["valor"] = None
        renderizar_tareas()

    def renderizar_tareas():
        tareas_a_mostrar = state["entregas"]
        if filtro_activo["tipo"] == "proximas":
            txt_titulo_lista.value = "Próximas (48h)"
            tareas_a_mostrar = [t for t in state["entregas"] if 0 <= obtener_tiempo_restante(t["fecha"])[3] <= 172800]
        elif filtro_activo["tipo"] == "materia":
            txt_titulo_lista.value = f"Materia: {filtro_activo['valor']}"
            tareas_a_mostrar = [t for t in state["entregas"] if t["materia"] == filtro_activo["valor"]]
        else:
            txt_titulo_lista.value = "Pendientes Críticos"

        pesos = {"Crítica": 0, "Media": 1, "Baja": 2}
        ordenadas = sorted(tareas_a_mostrar, key=lambda x: pesos.get(x.get("prio", "Media"), 1))
        lista_tareas_ui.controls = [crear_card_tarea(ent) for ent in ordenadas]
        if not tareas_a_mostrar:
            lista_tareas_ui.controls = [ft.Container(ft.Text("Sin tareas", italic=True, color="#64748b"), padding=20)]
        actualizar_dashboard()
        page.update()

    sb_filtros = ft.SegmentedButton(
        selected={"todos"},
        on_change=cambiar_filtro,
        segments=[
            ft.Segment(value="todos", label=ft.Text("Todo"), icon=ft.Icon(ft.Icons.ALL_INCLUSIVE)),
            ft.Segment(value="proximas", label=ft.Text("Próximo"), icon=ft.Icon(ft.Icons.TIMER_OUTLINED)),
        ],
    )

    txt_nueva_mat = ft.TextField(label="Nueva Materia", expand=True, border_radius=10)
    dd_materia = ft.Dropdown(label="Asignatura", expand=True, border_radius=10, options=[ft.dropdown.Option(m) for m in state["materias"]])
    dd_prio = ft.Dropdown(label="Prioridad", width=110, border_radius=10, options=[ft.dropdown.Option("Crítica"), ft.dropdown.Option("Media"), ft.dropdown.Option("Baja")], value="Media")
    txt_act = ft.TextField(label="Descripción", border_radius=10)
    txt_fec = ft.TextField(label="Fecha (DD/MM HH:MM)", border_radius=10, expand=True)

    def registrar(e):
        if not re.match(r"^\d{2}/\d{2} \d{2}:\d{2}$", txt_fec.value):
            txt_fec.error_text = "Formato: DD/MM HH:MM"; page.update(); return
        if not dd_materia.value or not txt_act.value: return
        nueva_data = {"materia": dd_materia.value, "actividad": txt_act.value, "fecha": txt_fec.value, "prio": dd_prio.value}
        if tarea_editando["ref"]:
            idx = state["entregas"].index(tarea_editando["ref"])
            state["entregas"][idx] = nueva_data
            tarea_editando["ref"] = None
            btn_registrar.text = "Guardar"; btn_registrar.bgcolor = "#f59e0b"; btn_registrar.icon = ft.Icons.PLAYLIST_ADD_ROUNDED
        else:
            state["entregas"].append(nueva_data)
        txt_act.value = ""; txt_fec.value = ""; txt_fec.error_text = None
        guardar_y_refrescar()

    btn_registrar = ft.FloatingActionButton(icon=ft.Icons.PLAYLIST_ADD_ROUNDED, bgcolor="#f59e0b", on_click=registrar, text="Guardar")

    def abrir_gestion(e):
        def borrar(m_nombre):
            state["materias"].remove(m_nombre)
            state["entregas"] = [t for t in state["entregas"] if t["materia"] != m_nombre]
            guardar_y_refrescar()
            # Corrección del error "mat is not defined" aquí:
            dlg.content.controls = [ft.ListTile(title=ft.Text(mat_item), trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda _, mi=mat_item: borrar(mi))) for mat_item in state["materias"]]
            page.update()
        
        # Corrección del error "mat is not defined" aquí también:
        dlg = ft.AlertDialog(
            title=ft.Text("Materias"), 
            content=ft.Column([ft.ListTile(title=ft.Text(mat_item), trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda _, mi=mat_item: borrar(mi))) for mat_item in state["materias"]], tight=True), 
            actions=[ft.TextButton("Cerrar", on_click=lambda _: (setattr(dlg, "open", False), page.update()))]
        )
        page.dialog = dlg; dlg.open = True; page.update()

    page.add(
        ft.Row([
            ft.CircleAvatar(content=ft.Text("JA"), bgcolor="#f59e0b", color="black"),
            ft.Column([ft.Text("Jose A Alcantara Aladin", size=18, weight="bold"), ft.Text("Gestión Académica TI", size=12, color="#94a3b8")], spacing=0, expand=True),
            ft.IconButton(ft.Icons.SETTINGS_SUGGEST_ROUNDED, on_click=abrir_gestion)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Column([txt_pct, pb_barra], spacing=5),
        ft.Text("Dashboard de Logros", size=11, weight="bold", color="#64748b"),
        dashboard_ui,
        ft.Divider(height=10, color="transparent"),
        ft.Row([sb_filtros], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=10, color="transparent"),
        ft.Row([txt_nueva_mat, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=lambda _: (state["materias"].append(txt_nueva_mat.value), txt_nueva_mat.update(value=""), guardar_y_refrescar()), icon_color="#f59e0b")]),
        ft.Row([dd_materia, dd_prio]),
        txt_act,
        ft.Row([txt_fec, btn_registrar]),
        ft.Divider(height=20, color="#334155"),
        ft.Row([txt_titulo_lista, ft.Text(f"{len(state['entregas'])} total", size=12, color="#64748b")]),
        lista_tareas_ui
    )
    renderizar_tareas(); actualizar_progreso(); actualizar_dashboard()

if __name__ == "__main__":
    ft.app(target=main)